"""Execute real server packets through the real firmware JSON parser and state machine."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest
from backend.models import Command, Telemetry, default_settings
from backend.state import Fleet

ROOT = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT/"esp32_software/firmware"


@pytest.fixture
def peer(tmp_path):
    compiler = shutil.which("clang++") or shutil.which("g++")
    library = FIRMWARE/".pio/libdeps/general-driver/ArduinoJson/src"
    if not compiler or not library.is_dir():
        if os.getenv("ACFIELD_REQUIRE_FIRMWARE_CONTRACT") == "1":
            pytest.fail("Firmware contract dependencies are required in this environment")
        pytest.skip("Install a host C++ compiler and run pio pkg install in firmware first")
    binary = tmp_path/"device-peer"
    subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror", "-I", str(library),
                    "-I", str(FIRMWARE/"include"), str(FIRMWARE/"test/device_peer.cpp"), "-o", str(binary)], check=True)
    process = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    def send(op="command", **kwargs):
        process.stdin.write(json.dumps({"op": op, **kwargs})+"\n")
        process.stdin.flush()
        return json.loads(process.stdout.readline())
    yield send
    process.stdin.close()
    process.wait(timeout=2)
    assert process.returncode == 0


def test_boot_lost_binding_arm_motion_timeout_and_reconnect(peer):
    f = Fleet(default_settings(), "hardware")
    r = f.robot("car-01")
    outgoing = []
    f.send = lambda packet, endpoint: outgoing.append(packet.copy())
    seq = 0
    def telemetry(status):
        nonlocal seq
        peer("sent", seq=seq, now=100+seq*2)
        data = {k: v for k, v in status.items() if k in ("device_state", "ack_session", "ack_seq", "stop_reason")}
        f.telemetry(Telemetry(version=1, type="telemetry", robot_id="car-01", boot_id="test-boot", seq=seq,
                              **data), ("127.0.0.1", 9998))
        seq += 1
    telemetry({"device_state": "unbound"})
    assert outgoing[0]["telemetry_seq"] == 0
    assert not r.bound
    with pytest.raises(ValueError, match="停车绑定"):
        f.arm(r, True)
    # Drop first binding stop; a retry must succeed through the actual parser.
    f.tick(time.monotonic()+.16)
    assert len(outgoing) >= 2 and outgoing[0]["seq"] == outgoing[-1]["seq"]
    status = peer(packet=outgoing[-1], now=101)
    assert status["accepted"] and status["device_state"] == "disarmed"
    telemetry(status)
    assert r.bound
    f.pose(r, 1, 1, 0, time.monotonic())
    f.arm(r, True)
    assert not r.armed and r.pending["action"] == "arm"
    status = peer(packet=outgoing[-1], now=103)
    assert status["accepted"] and status["device_state"] == "armed"
    telemetry(status)
    assert r.armed
    packet = f.command(r, Command(v=.1, omega=0))
    status = peer(packet=packet, now=105)
    assert status["accepted"] and status["v"] == pytest.approx(.1)
    assert not peer(packet=packet, now=300)["accepted"]
    status = peer("tick", now=405)
    assert status["device_state"] == "disarmed" and status["v"] == 0
    telemetry(status)
    assert not r.armed
    assert not peer(packet={**packet, "seq": 99}, now=406)["accepted"]
    # Local link loss explicitly invalidates historical acknowledgments.
    status = peer("link_lost", now=407)
    assert "ack_session" not in status
    telemetry(status)
    assert not r.bound and not r.armed


def test_zero_request_cannot_overtake_pending_disarm(peer):
    f = Fleet(default_settings(), "hardware")
    r = f.robot("car-01")
    # A device has already bound/armed and is moving.
    peer("sent", seq=0, now=100)
    common = {"version": 1, "type": "command", "robot_id": "car-01", "boot_id": "test-boot",
              "session": f.session, "telemetry_seq": 0, "ttl_ms": 300, "omega": 0}
    assert peer(packet={**common, "seq": 1, "action": "stop", "v": 0, "stop": True}, now=101)["accepted"]
    assert peer(packet={**common, "seq": 2, "action": "arm", "v": 0, "stop": True}, now=102)["accepted"]
    assert peer(packet={**common, "seq": 3, "action": "drive", "v": .1, "stop": False}, now=103)["accepted"]
    r.seq = 3
    r.boot_id, r.telemetry_seq, r.seen_at, r.endpoint = "test-boot", 0, time.monotonic(), ("127.0.0.1", 9998)
    r.bound, r.armed = True, True
    f.stop(r, "test stop")  # drop this packet
    assert not r.bound
    packet = f.command(r, Command(v=0, omega=0))
    assert packet["action"] == "stop"
    status = peer(packet=packet, now=104)
    assert status["accepted"] and status["device_state"] == "disarmed"
    f.telemetry(Telemetry(version=1, type="telemetry", robot_id="car-01", boot_id="test-boot", seq=1,
                          device_state="disarmed", ack_session=f.session, ack_seq=packet["seq"]), r.endpoint)
    assert r.bound and r.pending is None
