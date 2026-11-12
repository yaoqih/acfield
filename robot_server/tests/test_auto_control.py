"""Fresh input starts control; a stopped or expired input never starts later."""
import pytest

from backend.models import Command, Telemetry, default_settings
from backend.state import Fleet


@pytest.fixture
def hardware(monkeypatch):
    now = [100.]
    monkeypatch.setattr('backend.state.time.monotonic', lambda: now[0])
    fleet = Fleet(default_settings(), 'hardware')
    fleet.allow_unlocalized_control = True
    robot = fleet.robot('car-01')
    sent = []
    fleet.send = lambda packet, endpoint: sent.append(packet.copy())

    def telemetry(state, ack=None):
        fleet.telemetry(Telemetry(version=1, type='telemetry', robot_id='car-01',
            boot_id='boot', seq=robot.telemetry_seq+1, firmware='0.2.8',
            device_state=state, ack_session=fleet.session, ack_seq=ack,
            clock_synced=True), ('localhost', 9998))

    telemetry('unbound')
    telemetry('disarmed', robot.pending['seq'])
    assert robot.bound and not robot.armed
    return fleet, robot, now, sent, telemetry


def test_latest_input_runs_after_automatic_handshake_with_original_expiry(hardware):
    fleet, robot, now, sent, telemetry = hardware
    packet = fleet.command(robot, Command(v=.05, omega=0), 'page')
    assert packet['action'] == 'arm' and robot.target_v == 0
    now[0] += .025
    fleet.command(robot, Command(v=.08, omega=.1), 'page')
    assert [p['action'] for p in sent].count('arm') == 1
    now[0] += .05
    telemetry('armed', packet['seq'])
    assert robot.armed and robot.owner == 'page'
    assert sent[-1]['action'] == 'drive' and sent[-1]['v'] == .08
    assert sent[-1]['omega'] == .1 and 245 <= sent[-1]['ttl_ms'] <= 250
    assert 'execute_at_ms' in sent[-1]
    assert robot.deferred_command is None


def test_unscheduled_fresh_input_survives_clock_changes(hardware):
    fleet, robot, now, sent, telemetry = hardware
    robot.clock_synced = False
    arm = fleet.command(robot, Command(v=.05, omega=0), 'page')
    # The ACK may arrive before the device has synchronized.
    fleet.telemetry(Telemetry(version=1, type='telemetry', robot_id='car-01',
        boot_id='boot', seq=robot.telemetry_seq+1, firmware='0.2.8',
        device_state='armed', ack_session=fleet.session, ack_seq=arm['seq'],
        clock_synced=False), ('localhost', 9998))
    assert sent[-1]['v'] == .05 and 'execute_at_ms' not in sent[-1]
    robot.clock_synced = True
    fleet.command(robot, Command(v=.06, omega=0), 'page')
    assert sent[-1]['v'] == .06 and 'execute_at_ms' in sent[-1]
    robot.clock_synced = False
    fleet.command(robot, Command(v=.07, omega=0), 'page')
    assert sent[-1]['v'] == .07 and 'execute_at_ms' not in sent[-1]
    assert robot.armed and robot.owner == 'page'


@pytest.mark.parametrize('cancel', ['zero', 'release', 'timeout', 'late_ack', 'reboot'])
def test_cancelled_input_cannot_run_when_arm_ack_arrives(hardware, cancel):
    fleet, robot, now, sent, telemetry = hardware
    arm = fleet.command(robot, Command(v=.05, omega=0, ttl_ms=100), 'page')
    if cancel == 'zero':
        fleet.command(robot, Command(v=0, omega=0), 'page')
    elif cancel == 'release':
        fleet.release(robot, 'page')
    elif cancel == 'timeout':
        now[0] += .101
        fleet.tick(now[0])
    elif cancel == 'late_ack':
        now[0] += .101  # ACK may arrive before the next server tick.
    else:
        fleet.telemetry(Telemetry(version=1, type='telemetry', robot_id='car-01',
            boot_id='new-boot', seq=0, device_state='unbound'), robot.endpoint)
    telemetry('armed', arm['seq'])
    assert not robot.armed and robot.target_v == 0
    assert robot.deferred_command is None
    assert not any(p['action'] == 'drive' and p['v'] for p in sent)


def test_stop_and_reconnect_allow_fresh_input_without_resuming_old_input(hardware):
    fleet, robot, now, sent, telemetry = hardware
    arm = fleet.command(robot, Command(v=.05, omega=0), 'page')
    telemetry('armed', arm['seq'])
    now[0] += 3.1
    telemetry('disarmed')
    assert not robot.bound and not robot.armed and robot.deferred_command is None
    telemetry('disarmed', robot.pending['seq'])
    fleet.tick(now[0])
    assert robot.bound and robot.target_v == 0 and not robot.armed
    arm = fleet.command(robot, Command(v=-.04, omega=0), 'page')
    telemetry('armed', arm['seq'])
    assert robot.armed and robot.target_v == -.04
    assert sent[-1]['v'] == -.04


def test_normal_firmware_tolerates_1058ms_gap_without_stop_rebinding(hardware):
    fleet, robot, now, sent, telemetry = hardware
    before = len(sent)
    now[0] += 1.058
    fleet.tick(now[0])
    telemetry('disarmed')
    assert robot.bound and robot.pending is None
    assert fleet.snapshot()['robots'][0]['online']
    assert len(sent) == before


def test_invalid_batch_does_not_start_handshake_for_other_robots(hardware):
    fleet, robot, now, sent, telemetry = hardware
    before = len(sent)
    with pytest.raises(ValueError, match='设备离线'):
        fleet.commands({'car-01': Command(v=.05, omega=0),
                        'car-02': Command(v=.05, omega=0)}, 'page')
    assert robot.owner is None and robot.deferred_command is None
    assert len(sent) == before


def test_other_page_cannot_replace_input_while_handshake_is_pending(hardware):
    fleet, robot, now, sent, telemetry = hardware
    arm = fleet.command(robot, Command(v=.05, omega=0), 'first')
    with pytest.raises(ValueError, match='控制权'):
        fleet.command(robot, Command(v=-.05, omega=0), 'second')
    telemetry('armed', arm['seq'])
    assert robot.owner == 'first' and robot.target_v == .05
