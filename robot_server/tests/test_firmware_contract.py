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


@pytest.mark.parametrize("name", ["protocol", "motion", "scheduler", "time_sync", "encoder_feedback"])
def test_firmware_host_regressions(name, tmp_path):
    compiler = shutil.which("clang++") or shutil.which("g++")
    if not compiler:
        pytest.skip("Host C++ compiler is unavailable")
    binary = tmp_path/name
    subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror", "-I", str(FIRMWARE/"include"),
                    str(FIRMWARE/f"test/{name}_test.cpp"), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)


@pytest.mark.parametrize("diagnostic", [False, True])
def test_encoder_diagnostic_motor_behavior(diagnostic, tmp_path):
    compiler = shutil.which("clang++") or shutil.which("g++")
    if not compiler:
        pytest.skip("Host C++ compiler is unavailable")
    binary = tmp_path/"motors"
    flags = ["-DENCODER_DIAGNOSTIC"] if diagnostic else []
    subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror", *flags,
                    "-I", str(FIRMWARE/"test/fakes"), "-I", str(FIRMWARE/"include"),
                    str(FIRMWARE/"test/motors_diagnostic_test.cpp"), str(FIRMWARE/"src/motors.cpp"),
                    "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)


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
    # Fresh motion performs the arm handshake automatically, including with
    # the existing firmware protocol. No explicit /arm call is required.
    f.command(r, Command(v=.1, omega=0))
    assert not r.armed and r.pending["action"] == "arm"
    status = peer(packet=outgoing[-1], now=103)
    assert status["accepted"] and status["device_state"] == "armed"
    telemetry(status)
    assert r.armed
    packet = outgoing[-1]
    assert packet["action"] == "drive"
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


@pytest.mark.parametrize("invalid_voltage", [None, 0, 17])
def test_battery_sensor_warning_allows_arming_and_continuous_motion(peer, invalid_voltage):
    fleet = Fleet(default_settings(), "hardware")
    fleet.allow_unlocalized_control = True
    robot = fleet.robot("car-01")
    outgoing = []
    fleet.send = lambda packet, endpoint: outgoing.append(packet.copy())
    seq = 0

    def telemetry(status, now):
        nonlocal seq
        peer("sent", seq=seq, now=now)
        data = {k: status[k] for k in ("device_state", "ack_session", "ack_seq", "stop_reason", "fault", "warning")
                if k in status}
        fleet.telemetry(Telemetry(version=1, type="telemetry", robot_id=robot.config.id,
                                  boot_id="test-boot", seq=seq, **data), ("127.0.0.1", 9998))
        seq += 1

    # Even an invalid first sample must permit binding and explicit arming.
    status = peer("battery", voltage_v=invalid_voltage, now=100)
    assert status["warning"] == "battery_sensor" and status["fault"] is None
    telemetry(status, 100)
    telemetry(peer(packet=outgoing[-1], now=101), 102)
    assert robot.bound
    fleet.arm(robot, True)
    telemetry(peer(packet=outgoing[-1], now=103), 104)
    assert robot.armed and robot.warning == "battery_sensor"
    packet = fleet.command(robot, Command(v=.1, omega=0))
    assert peer(packet=packet, now=105)["accepted"]

    # Persistent warnings, recovery, and recurrence leave motion and ownership intact.
    for i, voltage in enumerate([invalid_voltage]*15 + [12.4, invalid_voltage, 12.4]):
        now = 200+i*100
        status = peer("battery", voltage_v=voltage, now=now)
        assert status["device_state"] == "armed" and status["v"] == pytest.approx(.1)
        assert status["fault"] is None
        expected_warning = None if voltage == 12.4 else "battery_sensor"
        assert status["warning"] == expected_warning
        telemetry(status, now)
        fleet.tick(time.monotonic())
        assert robot.armed and robot.owner == "local" and robot.pending is None
        assert fleet.ready(robot, time.monotonic()) is None
        assert fleet.snapshot()["robots"][0]["warning"] == expected_warning
        packet = fleet.command(robot, Command(v=.1, omega=0))
        assert peer(packet=packet, now=now+1)["accepted"]
        assert peer("tick", now=now+2)["device_state"] == "armed"

    # Missing readings interrupt the continuous low-voltage interval.
    assert peer("battery", voltage_v=10.4, now=2000)["fault"] is None
    status = peer("battery", voltage_v=invalid_voltage, now=2400)
    assert status["warning"] == "battery_sensor" and status["fault"] is None
    status = peer("battery", voltage_v=10.4, now=3000)
    assert status["fault"] is None and status["device_state"] == "armed"
    assert peer("battery", voltage_v=10.4, now=3999)["fault"] is None

    # Actual continuous undervoltage still latches and cannot be erased by recovery.
    status = peer("battery", voltage_v=10.4, now=4000)
    assert status["fault"] == "battery_low" and status["v"] == 0
    telemetry(status, 4000)
    assert not robot.armed
    status = peer("battery", voltage_v=12.4, now=4100)
    assert status["fault"] == "battery_low" and status["warning"] is None
    telemetry(status, 4100)
    with pytest.raises(ValueError, match="battery_low"):
        fleet.arm(robot, True)
