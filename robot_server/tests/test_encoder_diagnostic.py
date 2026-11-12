import time
import json

import pytest

from backend.clock import clock
from backend.models import Command, DeviceLimits, default_settings
from backend.state import Fleet
from backend.udp import DeviceProtocol


def diagnostic_fleet():
    fleet = Fleet(default_settings(), 'hardware')
    fleet.allow_unlocalized_control = True
    robot = fleet.robot('car-01')
    robot.firmware = '0.2.4-encoder-diagnostic'
    robot.limits = DeviceLimits(max_v=255/350, max_omega=.1)
    robot.seen_at = time.monotonic()
    robot.bound = robot.armed = True
    robot.owner = 'diagnostic-page'
    return fleet, robot


def test_diagnostic_motion_survives_clock_changes_but_expires():
    fleet, robot = diagnostic_fleet()
    assert fleet.snapshot()['robots'][0]['encoder_diagnostic'] == {'max_pwm': 255, 'pwm_per_mps': 350}
    for synced, pwm in [(False, 18), (True, 30), (False, -10)]:
        robot.clock_synced = synced
        packet = fleet.command(robot, Command(v=pwm/350, omega=0, ttl_ms=500, immediate=True), robot.owner)
        assert 'execute_at_ms' not in packet  # Do not let packet() add a schedule implicitly.
        assert 'immediate' not in packet  # Existing flashed firmware needs no wire extension.
        assert packet['v'] == pytest.approx(pwm/350)
        assert robot.armed
    fleet.tick(robot.deadline+.001)
    assert not robot.armed and robot.target_v == 0


@pytest.mark.parametrize('firmware', [None, '0.2.3', 'future-encoder-diagnostic'])
def test_immediate_motion_requires_a_known_diagnostic_profile(firmware):
    fleet, robot = diagnostic_fleet()
    robot.firmware = firmware
    with pytest.raises(ValueError, match='诊断固件'):
        fleet.command(robot, Command(v=.05, omega=0, immediate=True), robot.owner)
    assert not robot.armed


@pytest.mark.parametrize('fields', [
    {'v': 256/350, 'omega': 0},
    {'v': -256/350, 'omega': 0},
    {'v': .05, 'omega': .01},
    {'v': .05, 'omega': 0, 'execute_at_ms': 1},
])
def test_immediate_diagnostic_rejects_clipping_turns_and_schedules(fields):
    fleet, robot = diagnostic_fleet()
    with pytest.raises(ValueError, match='PWM|执行时间'):
        fleet.command(robot, Command(**fields, immediate=True), robot.owner)
    assert not robot.armed


def test_diagnostic_pwm_is_independent_of_speed_limit_and_respects_ownership():
    fleet, robot = diagnostic_fleet()
    robot.config.max_v = .02
    assert fleet.encoder_diagnostic(robot)['max_pwm'] == 255
    packet = fleet.command(robot, Command(v=255/350, omega=0, immediate=True), robot.owner)
    assert packet['v'] == pytest.approx(255/350)
    with pytest.raises(ValueError, match='控制权'):
        fleet.command(robot, Command(v=7/350, omega=0, immediate=True), 'another-page')
    assert robot.armed and robot.owner == 'diagnostic-page'


def test_legacy_firmware_keeps_its_actual_pwm_cap():
    fleet, robot = diagnostic_fleet()
    robot.firmware = '0.2.3-encoder-diagnostic'
    robot.limits = DeviceLimits(max_v=.1, max_omega=.1)
    assert fleet.encoder_diagnostic(robot)['max_pwm'] == 35
    with pytest.raises(ValueError, match='PWM'):
        fleet.command(robot, Command(v=36/350, omega=0, immediate=True), robot.owner)


def test_server_renews_diagnostic_without_browser_commands_and_zero_keeps_unlocked():
    fleet, robot = diagnostic_fleet()
    sent = []
    robot.endpoint, robot.telemetry_seq = ('localhost', 9998), 1
    fleet.send = lambda packet, endpoint: sent.append(packet)
    now = time.monotonic()
    fleet.command(robot, Command(v=100/350, omega=0, ttl_ms=500, immediate=True, hold=True), robot.owner)
    # More than the old 30s cutoff and 10s owner timeout with no further UI commands.
    for i in range(1, 1401):
        at = now+i*.025
        robot.seen_at, robot.telemetry_seq = at, i+1
        robot.clock_synced = i % 2 == 0
        fleet.tick(at)
    assert robot.armed and robot.owner == 'diagnostic-page'
    assert len(sent) == 1401 and sent[-1]['telemetry_seq'] == 1401
    assert all('execute_at_ms' not in p for p in sent)
    fleet.command(robot, Command(v=0, omega=0, ttl_ms=500, immediate=True, hold=True), robot.owner)
    fleet.tick(now+35.025)
    assert robot.armed and robot.target_v == 0 and robot.diagnostic_hold
    assert fleet.release(robot, robot.owner, '用户点击停车')
    before = len(sent)
    fleet.tick(now+35.050)
    assert not robot.armed and robot.diagnostic_hold is None
    assert all(packet['action'] == 'stop' for packet in sent[before:])


@pytest.mark.parametrize('failure', ['offline', 'fault', 'estop', 'firmware'])
def test_held_output_stops_on_real_failure_and_does_not_restart(failure):
    fleet, robot = diagnostic_fleet()
    fleet.command(robot, Command(v=.05, omega=0, immediate=True, hold=True), robot.owner)
    if failure == 'offline':
        robot.seen_at -= 4
    elif failure == 'fault':
        robot.fault = 'battery_low'
    elif failure == 'estop':
        fleet.estop = True
    else:
        robot.firmware = '0.2.3'
    fleet.tick(time.monotonic())
    assert not robot.armed and robot.diagnostic_hold is None
    robot.seen_at, robot.fault, fleet.estop = time.monotonic(), None, False
    fleet.tick(time.monotonic())
    assert not robot.armed and robot.target_v == 0


def test_hold_requires_immediate_diagnostic_even_at_zero():
    fleet, robot = diagnostic_fleet()
    with pytest.raises(ValueError, match='立即执行'):
        fleet.command(robot, Command(v=0, omega=0, hold=True), robot.owner)


def test_normal_commands_keep_scheduled_execution():
    fleet, robot = diagnostic_fleet()
    robot.firmware, robot.clock_synced = '0.2.3', True
    packet = fleet.command(robot, Command(v=.05, omega=0), robot.owner)
    assert 0 < packet['execute_at_ms']-clock.now_ms() <= 60


@pytest.mark.parametrize('condition,reason', [('fault', '设备故障'), ('estop', '全局停止'), ('offline', '设备离线')])
def test_immediate_motion_preserves_device_and_connection_checks(condition, reason):
    fleet, robot = diagnostic_fleet()
    if condition == 'fault':
        robot.fault = 'battery_low'
    elif condition == 'estop':
        fleet.estop = True
    else:
        robot.seen_at = time.monotonic()-4
    with pytest.raises(ValueError, match=reason):
        fleet.command(robot, Command(v=.05, omega=0, immediate=True), robot.owner)
    assert not robot.armed


def test_ws_holds_without_more_browser_messages_and_disconnect_releases(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app import create_app

    with TestClient(create_app(mode='demo', db_path=tmp_path/'config.db')) as client:
        fleet = client.app.state.fleet
        fleet.allow_unlocalized_control = True
        robot = fleet.robot('car-01')
        robot.firmware = '0.2.4-encoder-diagnostic'
        headers = {'X-Control-ID': 'diagnostic-page'}
        command = {'v': 18/350, 'omega': 0, 'ttl_ms': 500, 'immediate': True, 'hold': True}
        assert client.post('/api/robots/car-01/command', json=command, headers=headers).status_code == 422
        assert client.post('/api/commands', json={'car-01': command}, headers=headers).status_code == 422
        assert client.post('/api/robots/car-01/arm', json={'enabled': True}, headers=headers).status_code == 200
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'control', 'owner': 'diagnostic-page', 'seq': 1,
                          'robot_id': 'car-01', 'command': command})
            while (message := ws.receive_json()).get('type') != 'control_ack':
                assert message.get('type') != 'control_error'
            initial_seq = message['packet']['seq']
            time.sleep(.65)  # Exceeds the 500 ms device command TTL with no UI renewal.
            assert robot.armed and robot.seq > initial_seq+10
            assert robot.diagnostic_hold and robot.target_v == pytest.approx(18/350)
            # Retrying a past browser sequence cannot silently restart/replace output.
            ws.send_json({'type': 'control', 'owner': 'diagnostic-page', 'seq': 1,
                          'robot_id': 'car-01', 'command': command})
            deadline = time.monotonic()+1
            while robot.armed:
                assert time.monotonic() < deadline
                time.sleep(.01)
        assert not robot.armed and robot.diagnostic_hold is None
        assert robot.last_stop_reason == '控制连接断开 · 已停车'


def test_diagnostic_heartbeat_gap_of_1129ms_does_not_stop_or_rebind(monkeypatch):
    from backend.models import Telemetry
    fleet, robot = diagnostic_fleet()
    now = [100.]
    monkeypatch.setattr('backend.state.time.monotonic', lambda: now[0])
    robot.seen_at, robot.boot_id = now[0], 'same-boot'
    robot.endpoint, robot.telemetry_seq = ('localhost', 9998), 1
    fleet.command(robot, Command(v=.05, omega=0, ttl_ms=500, immediate=True, hold=True), robot.owner)
    now[0] += 1.129
    fleet.tick(now[0])
    assert robot.armed and fleet.snapshot()['robots'][0]['online']
    fleet.telemetry(Telemetry(version=1, type='telemetry', robot_id='car-01', boot_id='same-boot', seq=58,
                              firmware=robot.firmware, device_state='armed', motion_echo_rejections=0), robot.endpoint)
    assert robot.armed and robot.bound and robot.pending is None
    assert robot.motion_echo_rejections == 0
    # The relaxed threshold is finite; an actual telemetry loss still stops the run.
    now[0] += 3.001
    fleet.tick(now[0])
    assert not robot.armed and robot.diagnostic_hold is None and robot.last_stop_reason == '设备离线'
    fleet.telemetry(Telemetry(version=1, type='telemetry', robot_id='car-01', boot_id='same-boot', seq=200,
                              firmware=robot.firmware, device_state='armed'), robot.endpoint)
    assert not robot.armed and robot.last_stop_reason == '遥测中断 3001 ms 后恢复 · 等待停车确认'


def test_encoder_spikes_do_not_discard_heartbeat_ack_or_stop_motion(monkeypatch):
    fleet, robot = diagnostic_fleet()
    now = [100.]
    monkeypatch.setattr('backend.state.time.monotonic', lambda: now[0])
    robot.seen_at, robot.boot_id = now[0], 'same-boot'
    robot.endpoint, robot.telemetry_seq = ('127.0.0.1', 9998), 1
    fleet.command(robot, Command(v=.05, omega=0, ttl_ms=500, immediate=True, hold=True), robot.owner)
    protocol = DeviceProtocol(fleet)
    # Reproduce >1 s of encoder interference through the actual UDP decoder.
    # Old +/-3 m/s and +/-30 rad/s feedback limits discarded every one of these.
    for i in range(1, 47):
        now[0] = 100+i*.025
        packet = dict(version=1, type='telemetry', robot_id='car-01', boot_id='same-boot', seq=i+1,
                      firmware=robot.firmware, device_state='armed', encoder_left=-i*750, encoder_right=i*750,
                      wheel_left=55.6, wheel_right=-55.6, measured_v=4.5, measured_omega=-911.5,
                      ack_session=fleet.session, ack_seq=robot.seq)
        protocol.datagram_received(json.dumps(packet).encode(), robot.endpoint)
        fleet.tick(now[0])
    assert robot.armed and robot.bound and robot.diagnostic_hold
    assert robot.seen_at == now[0] and robot.telemetry_seq == 47
    assert robot.ack_seq == robot.seq-1 and robot.last_stop_reason is None
    assert protocol.received == 46 and protocol.rejected == 0
    snapshot = fleet.snapshot()['robots'][0]
    assert snapshot['online'] and snapshot['encoder_left'] == -34500
    assert snapshot['wheel_left'] == 55.6 and snapshot['measured_omega'] == -911.5


@pytest.mark.parametrize('field', ['measured_v', 'measured_omega', 'wheel_left', 'wheel_right'])
@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_feedback_is_rejected_and_has_a_diagnostic_record(field, value):
    fleet, robot = diagnostic_fleet()
    records = []
    fleet.record = lambda kind, data: records.append((kind, data))
    protocol = DeviceProtocol(fleet)
    before = robot.seen_at
    packet = dict(version=1, type='telemetry', robot_id='car-01', boot_id='same-boot', seq=1, **{field: value})
    protocol.datagram_received(json.dumps(packet).encode(), ('127.0.0.1', 9998))
    assert robot.seen_at == before
    assert protocol.received == protocol.rejected == 1
    assert protocol.rejection_counts == {'telemetry_validation': 1}
    assert records == [('udp_rejected', {'endpoint': ['127.0.0.1', 9998],
                                       'reason': 'telemetry_validation', 'fields': [field]})]


def test_diagnostic_two_minute_limit_is_on_server_and_updates_do_not_extend_it(monkeypatch):
    fleet, robot = diagnostic_fleet()
    now = [100.]
    monkeypatch.setattr('backend.state.time.monotonic', lambda: now[0])
    robot.seen_at = now[0]
    cmd = Command(v=.05, omega=0, ttl_ms=500, immediate=True, hold=True)
    fleet.command(robot, cmd, robot.owner)
    assert robot.diagnostic_until == 220
    for at in (130, 180, 219.9):
        now[0] = robot.seen_at = at
        fleet.tick(at)
        assert robot.armed
    fleet.command(robot, cmd.model_copy(update={'v': .1}), robot.owner)
    assert robot.diagnostic_until == 220  # Applying output must not restart the timer.
    now[0] = robot.seen_at = 220
    fleet.tick(220)
    assert not robot.armed and robot.diagnostic_hold is None
    assert robot.last_stop_reason == '达到 120 秒运行上限 · 已停车'
