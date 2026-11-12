import json
import math
import socket
import time

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.models import Command, DeviceLimits, Telemetry, default_settings
from backend.state import Fleet, POSE_TTL


def ready_fleet(mode="demo"):
    fleet = Fleet(default_settings(), mode)
    r = fleet.robot("car-01")
    now = time.monotonic()
    r.seen_at = now
    r.bound = True
    fleet.pose(r, 1, 1, 0, now)
    return fleet, r, now


def test_arm_limits_and_expiry():
    fleet, r, now = ready_fleet()
    fleet.command(r, Command(v=.2, omega=0))
    assert r.armed and r.owner == "local"
    packet = fleet.command(r, Command(v=1, omega=6, ttl_ms=100))
    assert packet["v"] == fleet.limits(r)[0]
    assert packet["omega"] == fleet.limits(r)[1]
    fleet.tick(now + .15)
    assert r.target_v == 0 and r.target_omega == 0
    assert r.command_status == "expired"


@pytest.mark.parametrize("mode,reported,expected", [
    ("demo", None, (.50, 1.50)),
    ("hardware", None, (.10, .30)),
    ("hardware", (.89, 3.00), (.50, 1.50)),
    ("hardware", (.20, .80), (.20, .80)),
])
def test_1_20_limits_respect_configuration_and_device(mode, reported, expected):
    fleet, r, _ = ready_fleet(mode)
    if reported:
        r.limits = DeviceLimits(max_v=reported[0], max_omega=reported[1])
    assert fleet.limits(r) == expected
    # Exercise clipping in both directions independently of arena geometry.
    fleet.allow_unlocalized_control = True
    r.armed, r.owner = True, "local"
    for sign in (-1, 1):
        packet = fleet.command(r, Command(v=sign, omega=sign*6))
        assert packet["v"] == sign*expected[0]
        assert packet["omega"] == sign*expected[1]


def test_pose_expiry_and_estop_never_rearm():
    fleet, r, now = ready_fleet()
    fleet.arm(r, True)
    fleet.command(r, Command(v=.2, omega=0))
    fleet.tick(now + POSE_TTL + .01)
    assert not r.armed and r.target_v == 0
    fleet.stop_all()
    with pytest.raises(ValueError, match="全局停止"):
        fleet.arm(r, True)
    fleet.estop = False
    assert not r.armed
    assert fleet.command(r, Command(v=0, omega=0))["stop"]


def test_udp_order_boot_restart_and_ack_session():
    fleet, r, _ = ready_fleet("hardware")
    def telemetry(seq, boot="first", **kwargs):
        return Telemetry(version=1, type="telemetry", robot_id=r.config.id, boot_id=boot, seq=seq, **kwargs)
    fleet.telemetry(telemetry(5, battery=80), ("127.0.0.1", 1234))
    binding = r.pending
    assert binding["telemetry_seq"] == 5
    fleet.telemetry(telemetry(6, device_state="disarmed", ack_session=fleet.session,
                              ack_seq=binding["seq"], battery=80), ("127.0.0.1", 1234))
    fleet.arm(r, True)
    arm_seq = r.pending["seq"]
    fleet.telemetry(telemetry(7, device_state="armed", ack_session=fleet.session,
                              ack_seq=arm_seq, battery=80), ("127.0.0.1", 1234))
    packet = fleet.command(r, Command(v=.1, omega=0))
    fleet.telemetry(telemetry(4, battery=10), ("127.0.0.1", 1234))
    assert r.battery == 80
    fleet.telemetry(telemetry(8, device_state="armed", ack_session="old-session", ack_seq=packet["seq"]), ("127.0.0.1", 1234))
    assert r.command_status == "sent"
    fleet.telemetry(telemetry(9, device_state="armed", ack_session=fleet.session, ack_seq=packet["seq"]), ("127.0.0.1", 1234))
    assert r.command_status == "confirmed"
    fleet.telemetry(telemetry(0, boot="second"), ("127.0.0.1", 1234))
    assert not r.armed and r.target_v == 0
    fleet.telemetry(telemetry(8), ("127.0.0.1", 1234))
    assert r.boot_id == "second"


def test_timeout_reason_survives_stop_binding_confirmation():
    fleet, r, _ = ready_fleet("hardware")
    r.boot_id, r.telemetry_seq = "first", 5
    r.armed, r.owner = True, "test"
    fleet.telemetry(Telemetry(version=1, type="telemetry", robot_id=r.config.id, boot_id="first", seq=6,
                              device_state="disarmed", stop_reason="command_timeout"), ("127.0.0.1", 1234))
    stop_seq = r.pending["seq"]
    fleet.telemetry(Telemetry(version=1, type="telemetry", robot_id=r.config.id, boot_id="first", seq=7,
                              device_state="disarmed", stop_reason="server_stop", ack_session=fleet.session,
                              ack_seq=stop_seq), ("127.0.0.1", 1234))
    state = fleet.snapshot()["robots"][0]
    assert state["stop_reason"] == "server_stop"
    assert state["last_stop_reason"] == "车端已停机：command_timeout"
    assert state["bound"] and not state["armed"]


def test_rotated_collision_box():
    fleet, r, now = ready_fleet()
    fleet.pose(r, 1, 2, math.pi/2, now+.01)
    corners = fleet.snapshot()["robots"][0]["corners"]
    assert max(p[0] for p in corners)-min(p[0] for p in corners) == pytest.approx(r.config.width)
    assert max(p[1] for p in corners)-min(p[1] for p in corners) == pytest.approx(r.config.length)


def test_api_websocket_config_and_persistence(tmp_path):
    path = tmp_path / "config.sqlite3"
    with TestClient(create_app(db_path=path)) as client:
        client.headers["X-Control-ID"] = "test-owner"
        assert client.get("/api/health").json()["status"] == "ok"
        with client.websocket_connect("/ws") as ws:
            state = ws.receive_json()
            assert len(state["robots"]) == 4
        assert client.post("/api/robots/car-01/arm", json={"enabled": True}).status_code == 200
        config = client.get("/api/config").json()
        assert client.put("/api/config", json=config).status_code == 409
        assert client.post("/api/robots/car-01/command", json={"v": .2, "omega": 0}).status_code == 200
        time.sleep(.15)
        assert client.get("/api/state").json()["robots"][0]["x"] > .84
        assert client.post("/api/stop").status_code == 200
        assert client.post("/api/robots/car-01/arm", json={"enabled": True}).status_code == 409
        config["robots"][0]["name"] = "测试小车"
        assert client.put("/api/config", json=config).status_code == 200
        assert client.get("/api/state").json()["estop"]
        config["robots"][1]["tag_id"] = config["robots"][0]["tag_id"]
        assert client.put("/api/config", json=config).status_code == 422
        assert client.post("/api/robots/unknown/arm", json={"enabled": True}).status_code == 404
        assert client.post("/api/robots/car-01/command", content='{"v":NaN,"omega":0}', headers={"Content-Type": "application/json"}).status_code == 422
    with TestClient(create_app(db_path=path)) as client:
        assert client.get("/api/config").json()["robots"][0]["name"] == "测试小车"
        assert not client.get("/api/state").json()["robots"][0]["armed"]


def test_vehicle_list_changes_and_simulator_positions(tmp_path):
    path = tmp_path / 'vehicles.sqlite3'
    with TestClient(create_app(db_path=path)) as client:
        client.headers['X-Control-ID'] = 'test-owner'
        config = client.get('/api/config').json()
        template = config['robots'][0]
        config['robots'] = [dict(template, id=f'car-{i:02}', name=f'Car {i}', tag_id=i) for i in range(16)]
        assert client.put('/api/config', json=config).status_code == 200
        state = client.get('/api/state').json()
        positions = {(r['x'], r['y']) for r in state['robots']}
        assert len(positions) == 16
        assert all(0 <= r['battery'] <= 100 for r in state['robots'])
        assert state['estop'] and all(not r['armed'] for r in state['robots'])
        config['robots'][1]['id'] = config['robots'][0]['id']
        assert client.put('/api/config', json=config).status_code == 422
        config['robots'][1]['id'] = 'car-01'
        config['robots'].pop(0)
        assert client.put('/api/config', json=config).status_code == 200
        assert client.post('/api/robots/car-00/arm', json={'enabled': True}).status_code == 404
        assert client.put('/api/config', json={**config, 'robots': []}).status_code == 422
        assert client.put('/api/config', json={**config, 'robots': config['robots'] + [template, dict(template, id='extra', tag_id=100)]}).status_code == 422
    with TestClient(create_app(db_path=path)) as client:
        assert [r['id'] for r in client.get('/api/config').json()['robots']] == [f'car-{i:02}' for i in range(1, 16)]


def test_hardware_real_udp_datagram(tmp_path):
    with TestClient(create_app(mode="hardware", db_path=tmp_path/"real.db", udp_port=0)) as client:
        client.headers["X-Control-ID"] = "test-owner"
        endpoint = client.app.state.udp.transport.get_extra_info("sockname")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as device:
            device.bind(("127.0.0.1", 0))
            device.settimeout(1)
            device.sendto(b'{"version":1,"type":"telemetry","robot_id":"car-01","boot_id":"test","seq":1,"battery":77}', endpoint)
            packet = json.loads(device.recv(4096))
            assert packet["stop"] and packet["robot_id"] == "car-01"
            state = client.get("/api/state").json()["robots"][0]
            assert packet["telemetry_seq"] == 1
            assert packet["action"] == "stop"
            assert state["online"] and state["battery"] == 77
            assert not state["visible"] and not state["armed"]
            assert client.post("/api/robots/car-01/arm", json={"enabled": True}).status_code == 409
            device.sendto(b'{bad json', endpoint)
            device.sendto(b'x'*5000, endpoint)
            time.sleep(.05)
            assert client.app.state.udp.rejected == 2
            health = client.get('/api/health').json()
            assert health['udp_received'] == 3 and health['udp_rejected'] == 2
            assert health['udp_rejections'] == {'invalid_message': 1, 'datagram_too_large': 1}


def test_mode_switch_replaces_session_stops_and_isolates_hardware(tmp_path):
    app = create_app(mode='demo', db_path=tmp_path/'config.db', udp_port=0)
    with TestClient(app, headers={'X-Control-ID': 'mode-test'}) as client:
        initial = client.get('/api/state').json()
        assert client.post('/api/robots/car-01/arm', json={'enabled': True}).status_code == 200
        assert client.post('/api/robots/car-01/command', json={'v': .05, 'omega': 0}).status_code == 200
        assert client.put('/api/mode', json={'mode': 'hardware'}).status_code == 200
        hardware = client.get('/api/state').json()
        assert hardware['mode'] == 'hardware' and hardware['session'] != initial['session']
        assert hardware['estop'] and all(not r['armed'] and not r['visible'] for r in hardware['robots'])
        assert client.get('/api/health').json()['mode'] == 'hardware'
        assert app.state.udp.transport.get_extra_info('sockname')[1] > 0
        assert client.put('/api/mode', json={'mode': 'demo'}).status_code == 200
        demo = client.get('/api/state').json()
        assert demo['mode'] == 'demo' and demo['session'] != hardware['session']
        assert demo['estop'] and all(not r['armed'] for r in demo['robots'])
        assert app.state.transport is None and app.state.udp is None
        assert client.post('/api/robots/car-01/arm', json={'enabled': True}).status_code == 409


def test_mode_switch_udp_failure_stays_in_demo_and_stops(tmp_path):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as occupied:
        occupied.bind(('127.0.0.1', 0))
        app = create_app(mode='demo', db_path=tmp_path/'config.db', udp_port=occupied.getsockname()[1])
        with TestClient(app, headers={'X-Control-ID': 'mode-test'}) as client:
            assert client.post('/api/robots/car-01/arm', json={'enabled': True}).status_code == 200
            assert client.put('/api/mode', json={'mode': 'hardware'}).status_code == 409
            state = client.get('/api/state').json()
            assert state['mode'] == 'demo' and state['estop']
            assert all(not r['armed'] for r in state['robots'])
            assert app.state.transport is None


def test_mode_switch_preserves_vision_sync_failure(tmp_path):
    app = create_app(mode='demo', db_path=tmp_path/'config.db', udp_port=0)
    with TestClient(app, headers={'X-Control-ID': 'mode-test'}) as client:
        app.state.fleet.vision_sync_error = '视觉配置同步失败'
        settings = client.get('/api/config').json()
        assert client.put('/api/config', json=settings).status_code == 200
        assert app.state.fleet.vision_sync_error == '视觉配置同步失败'
        assert client.put('/api/mode', json={'mode': 'hardware'}).status_code == 200
        assert app.state.fleet.vision_sync_error == '视觉配置同步失败'
        assert client.put('/api/mode', json={'mode': 'demo'}).status_code == 200
        assert client.post('/api/reset-stop').status_code == 200
        assert client.post('/api/robots/car-01/arm', json={'enabled': True}).status_code == 409


def test_vision_offset_frozen_frame_and_demo_rejection(monkeypatch):
    import asyncio
    import contextlib
    import httpx
    from backend.vision import watch

    async def scenario(demo):
        fleet, r, _ = ready_fleet("hardware")
        r.pose_at = 0
        r.config.tag_offset_x = .1
        fleet.arm(r, False)
        data = {"timestamp_utc": "fixed", "frame_id": 1, "frame_age_ms": 0,
                "status": "running", "demo": demo, "fps": 25,
                "source_kind": "camera", "world_calibrated": True, "family": "tag36h11",
                "tags": [{"id": 10, "status": "visible", "world_xyz_m": [1, 2, 0],
                          "heading_world_deg": 90, "age_ms": 0}]}
        original_client = httpx.AsyncClient
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=data))
        with monkeypatch.context() as patch:
            patch.setattr("backend.vision.httpx.AsyncClient", lambda **kwargs: original_client(transport=transport, **kwargs))
            task = asyncio.create_task(watch(fleet, "http://vision"))
            try:
                await asyncio.sleep(.06)
                if demo:
                    assert r.pose_at == 0
                    assert not fleet.camera["connected"]
                else:
                    assert r.x == pytest.approx(1)
                    assert r.y == pytest.approx(1.9)
                    r.bound = True
                    r.armed = True
                    r.owner_until = time.monotonic()+10
                    pose_at = r.pose_at
                    await asyncio.sleep(.22)
                    fleet.tick(time.monotonic())
                    assert r.pose_at == pose_at  # Repeated HTTP frame is not a new observation.
                    assert not r.armed
                    assert r.reason == "定位已过期"
            finally:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
    asyncio.run(scenario(False))
    asyncio.run(scenario(True))


def test_unlocalized_control_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("ROBOT_ALLOW_UNLOCALIZED_CONTROL", raising=False)
    fleet, r, now = ready_fleet()
    r.pose_at = 0
    assert fleet.ready(r, now) == "定位已过期"
    assert fleet.snapshot()["allow_unlocalized_control"] is False

    monkeypatch.setenv("ROBOT_ALLOW_UNLOCALIZED_CONTROL", "1")
    fleet, r, now = ready_fleet()
    r.x = r.y = r.theta = None
    r.pose_at = 0
    assert fleet.snapshot()["allow_unlocalized_control"] is True
    fleet.arm(r, True)
    fleet.command(r, Command(v=.05, omega=0, ttl_ms=100))
    fleet.tick(time.monotonic() + .15)
    assert not r.armed and r.target_v == 0
    assert r.command_status == "expired"


@pytest.mark.parametrize("expiry", ["owner", "heartbeat"])
def test_unlocalized_control_preserves_liveness_checks(monkeypatch, expiry):
    monkeypatch.setenv("ROBOT_ALLOW_UNLOCALIZED_CONTROL", "1")
    fleet, r, now = ready_fleet()
    r.pose_at = 0
    fleet.arm(r, True)
    if expiry == "owner":
        r.owner_until = now - 1
    else:
        r.seen_at = now - 4
    fleet.tick(now)
    assert not r.armed and r.owner is None
    assert r.target_v == r.target_omega == 0
