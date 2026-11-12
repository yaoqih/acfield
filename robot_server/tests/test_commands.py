import json
import time

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.models import Command, default_settings
from backend.state import Fleet
from backend.vision import ingest


def convoy():
    settings = default_settings()
    settings.robots = settings.robots[:2]
    for config in settings.robots:
        config.length = config.width = .13
        config.body_offset_x = .016
    fleet = Fleet(settings, "demo")
    now = time.monotonic()
    for r, x in zip(fleet.robots.values(), (1., 1.35)):
        r.seen_at = now
        fleet.pose(r, x, 1., 0., now)
        fleet.arm(r, True, "script")
    return fleet


@pytest.mark.parametrize("order", [("car-01", "car-02"), ("car-02", "car-01")])
def test_joint_motion_does_not_depend_on_request_order(order):
    fleet = convoy()
    packets = fleet.commands({ident: Command(v=.1, omega=0) for ident in order}, "script")
    assert all(packet["v"] == .1 for packet in packets.values())
    fleet.tick(time.monotonic())
    assert all(r.armed and r.target_v == .1 for r in fleet.robots.values())


def test_unsafe_batch_sends_no_partial_motion_and_logs_reason():
    fleet = convoy()
    records = []
    fleet.record = lambda kind, data: records.append((kind, data))
    with pytest.raises(ValueError, match="距离"):
        fleet.commands({"car-01": Command(v=.1, omega=0), "car-02": Command(v=-.1, omega=0)}, "script")
    assert all(not r.armed and r.target_v == 0 for r in fleet.robots.values())
    assert all(data["stop"] for kind, data in records if kind == "command")
    rejected = next(data for kind, data in records if kind == "control")
    assert not rejected["accepted"] and rejected["reason"] == "车间距离保护"
    assert rejected["requested"]["car-02"]["v"] == -.1


def test_batch_ownership_and_unknown_robot_do_not_partially_drive():
    fleet = convoy()
    fleet.robot("car-02").owner = "other"
    with pytest.raises(ValueError, match="控制权"):
        fleet.commands({ident: Command(v=.1, omega=0) for ident in fleet.robots}, "script")
    assert not fleet.robot("car-01").armed
    assert fleet.robot("car-02").armed and fleet.robot("car-02").owner == "other"
    before = fleet.robot("car-02").seq
    with pytest.raises(KeyError):
        fleet.commands({"car-02": Command(v=.1, omega=0), "missing": Command(v=0, omega=0)}, "other")
    assert fleet.robot("car-02").seq == before


def test_batch_api_validates_and_records_raw_and_applied_velocities(tmp_path):
    app = create_app(db_path=tmp_path/"config.db")
    with TestClient(app) as client:
        ids = ("car-01", "car-02")
        # Existing per-robot limits still override the faster motor defaults.
        settings = client.get("/api/config").json()
        for robot in settings["robots"]:
            robot["max_v"] = .1
        assert client.put("/api/config", json=settings).status_code == 200
        assert client.post("/api/reset-stop").status_code == 200
        deadline = time.monotonic() + 2
        while not all(r["online"] for r in client.get("/api/state").json()["robots"]):
            assert time.monotonic() < deadline, "Demo devices did not become ready"
            time.sleep(.01)
        body = {ident: {"v": .35, "omega": 0} for ident in ids}
        assert client.post("/api/commands", json=body).status_code == 422
        client.headers["X-Control-ID"] = "script"
        for ident in ids:
            assert client.post(f"/api/robots/{ident}/arm", json={"enabled": True}).status_code == 200
        response = client.post("/api/commands", json=body)
        assert response.status_code == 200
        assert all(p["v"] == .1 for p in response.json().values())
        assert client.post("/api/commands", json={}).status_code == 422
        assert client.post("/api/commands", json={"missing": {"v": 0, "omega": 0}}).status_code == 404
        assert client.post("/api/commands", json={"car-01": {"v": .1}}).status_code == 422
    rows = [json.loads(line) for line in next((tmp_path/"runs").glob("*/events.jsonl")).read_text().splitlines()]
    accepted = next(row["data"] for row in rows if row["kind"] == "control" and row["data"]["accepted"])
    assert accepted["requested"]["car-01"]["v"] == .35
    assert accepted["applied"]["car-01"]["v"] == .1


def test_health_distinguishes_service_alive_from_devices_ready(tmp_path):
    with TestClient(create_app(mode="hardware", db_path=tmp_path/"config.db", udp_port=0)) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["ready"] is False


def test_vision_jump_locks_and_cannot_silently_resume(monkeypatch):
    fleet = convoy()
    r = fleet.robot("car-01")
    clock = [time.monotonic()+.04]
    monkeypatch.setattr("backend.vision.time.monotonic", lambda: clock[0])
    frame = {"status": "running", "demo": False, "source_kind": "camera", "world_calibrated": True,
             "family": "tag36h11", "timestamp_utc": "frame", "frame_id": 1, "frame_age_ms": 0,
             "tags": [{"id": 10, "status": "visible", "world_xyz_m": [2., 2., .0646],
                       "heading_world_deg": 0., "age_ms": 0., "min_edge_px": 50.,
                       "decision_margin": None, "hamming": None}]}
    last = ingest(fleet, frame, clock[0], None)
    assert r.pose_at == 0 and not r.armed
    assert "跳变" in r.reason
    clock[0] += .04
    frame["frame_id"] = 2
    ingest(fleet, frame, clock[0], last)
    assert r.pose_at > 0 and not r.armed  # reacquiring a pose never resumes motion


@pytest.mark.parametrize("quality", [{"min_edge_px": 4}, {"decision_margin": 1}, {"hamming": 2}])
def test_low_quality_pose_invalidates_current_control(quality):
    fleet = convoy()
    frame = {"status": "running", "demo": False, "source_kind": "camera", "world_calibrated": True,
             "family": "tag36h11", "timestamp_utc": "frame", "frame_id": 1, "frame_age_ms": 0,
             "tags": [{"id": 10, "status": "visible", "world_xyz_m": [1., 1., .0646],
                       "heading_world_deg": 0., "age_ms": 0., **quality}]}
    ingest(fleet, frame, time.monotonic(), None)
    r = fleet.robot("car-01")
    assert r.pose_at == 0 and not r.armed
    assert "质量" in r.reason
