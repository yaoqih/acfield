import asyncio
import contextlib
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.models import Command, Telemetry, default_settings
from backend.state import Fleet
from backend.vision import ingest, watch


def demo():
    f = Fleet(default_settings(), "demo")
    r = f.robot("car-01")
    r.seen_at = time.monotonic()
    f.pose(r, 1, 1, 0, time.monotonic())
    return f, r


def test_expiry_stops_and_fresh_input_can_resume_without_unlock():
    f, r = demo()
    f.arm(r, True, "alice")
    with pytest.raises(ValueError, match="另一"):
        f.command(r, Command(v=.05, omega=0), "bob")
    with pytest.raises(ValueError, match="另一"):
        f.arm(r, True, "bob")
    f.command(r, Command(v=.05, omega=0, ttl_ms=100), "alice")
    f.tick(time.monotonic()+.11)
    assert not r.armed and r.owner is None
    f.command(r, Command(v=.05, omega=0), "alice")
    assert r.armed and r.owner == "alice"
    # Anyone may stop, including a page that has no control lease.
    assert f.command(r, Command(v=0, omega=0), "bob")["stop"]


def test_boundary_and_neighbour_sweeps_stop_real_mode():
    f, r = demo()
    f.pose(r, .05, 1, 0, time.monotonic()+.001)
    f.arm(r, True)
    with pytest.raises(ValueError, match="边界"):
        f.command(r, Command(v=.05, omega=0))
    assert not r.armed
    f.pose(r, 1, 1, 0, time.monotonic()+.002)
    other = f.robot("car-02")
    f.pose(other, 1.3, 1, 3.14159, time.monotonic())
    f.arm(r, True)
    with pytest.raises(ValueError, match="距离"):
        f.command(r, Command(v=.1, omega=0))
    assert not r.armed


def test_idle_owner_expires_and_body_offset_is_drawn():
    f, r = demo()
    f.arm(r, True)
    r.owner_until = time.monotonic()-.01
    f.tick(time.monotonic())
    assert not r.armed
    r.config.length = .13
    r.config.body_offset_x = .016
    xs = [p[0] for p in f.snapshot()["robots"][0]["corners"]]
    assert min(xs) == pytest.approx(1-.049)
    assert max(xs) == pytest.approx(1+.081)


def camera_frame(**changes):
    data = {"status": "running", "demo": False, "source_kind": "camera",
            "world_calibrated": True, "family": "tag36h11", "timestamp_utc": "frame-1",
            "frame_id": 1, "frame_age_ms": 0, "fps": 25,
            "tags": [{"id": 10, "status": "visible", "world_xyz_m": [1, 2, .0646],
                      "heading_world_deg": 0, "age_ms": 0}]}
    data.update(changes)
    return data


@pytest.mark.parametrize("changes", [{"source_kind": "file"}, {"demo": True},
    {"world_calibrated": False}, {"source_kind": None}, {"frame_age_ms": True},
    {"frame_id": None}, {"family": "tag16h5"}])
def test_only_calibrated_live_frames_are_accepted(changes):
    f, r = demo()
    ingest(f, camera_frame(**changes), time.monotonic(), None)
    assert r.pose_at == 0 and not f.camera["connected"]


def test_bad_tag_does_not_hide_valid_tag_or_poison_duplicates():
    f, r = demo()
    r.pose_at = 0
    data = camera_frame()
    data["tags"].append({"id": 11, "status": "visible", "world_xyz_m": [1.]})
    frame = ingest(f, data, time.monotonic(), None)
    assert r.pose_at > 0
    at = r.pose_at
    assert ingest(f, data, time.monotonic(), frame) == frame
    assert r.pose_at == at
    data["frame_id"] = 2
    data["tags"].append(data["tags"][0].copy())
    ingest(f, data, time.monotonic(), frame)
    assert r.pose_at == at  # a duplicate identity is not a new observation


def test_vision_watcher_survives_malformed_response(monkeypatch):
    async def scenario():
        f, r = demo()
        r.pose_at = 0
        count = 0
        def reply(request):
            nonlocal count
            count += 1
            if count == 1:
                return httpx.Response(200, json=camera_frame(tags=[{"id": 10, "status": "visible", "world_xyz_m": [1.]}]))
            return httpx.Response(200, json=camera_frame(frame_id=count))
        original = httpx.AsyncClient
        monkeypatch.setattr("backend.vision.httpx.AsyncClient", lambda **kw: original(transport=httpx.MockTransport(reply)))
        task = asyncio.create_task(watch(f, "http://vision"))
        try:
            await asyncio.sleep(.12)
            assert not task.done() and r.pose_at > 0
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
    asyncio.run(scenario())


def test_critical_task_failure_locks_and_degrades_health(tmp_path, monkeypatch):
    async def broken(fleet, url):
        raise IndexError("bad source")
    monkeypatch.setattr("backend.app.watch", broken)
    with TestClient(create_app(mode="hardware", db_path=tmp_path/"config.db", udp_port=0, vision_url="http://test")) as client:
        for _ in range(50):
            response = client.get("/api/health")
            if response.status_code == 503:
                break
            time.sleep(.01)
        assert response.status_code == 503
        assert response.json()["fault"] == "vision: IndexError"
        assert client.get("/api/state").json()["estop"]
        client.post("/api/reset-stop")
        assert client.get("/api/health").status_code == 503


def test_recording_contains_config_commands_and_poses(tmp_path):
    with TestClient(create_app(db_path=tmp_path/"config.db")) as client:
        client.headers["X-Control-ID"] = "owner"
        assert client.post("/api/robots/car-01/arm", json={"enabled": True}).status_code == 200
        assert client.post("/api/robots/car-01/command", json={"v": .05, "omega": 0}).status_code == 200
    folders = list((tmp_path/"runs").iterdir())
    assert len(folders) == 1
    metadata = json.loads((folders[0]/"config.json").read_text())
    rows = [json.loads(line) for line in (folders[0]/"events.jsonl").read_text().splitlines()]
    assert metadata["settings"]["robots"][0]["id"] == "car-01"
    assert {"command", "pose", "event", "startup"}.issubset(row["kind"] for row in rows)
