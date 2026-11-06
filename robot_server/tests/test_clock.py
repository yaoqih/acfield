import asyncio
import socket
import struct
import time

import pytest
from backend.clock import Clock
from backend.udp import DeviceProtocol
from backend.state import Fleet
from backend.models import default_settings


def test_clock_slews_without_wall_clock_steps(monkeypatch):
    c = Clock()
    mono = time.monotonic()
    monkeypatch.setattr(time, 'monotonic', lambda: mono)
    before = c.now_ms()
    c.target = -3600
    mono += 1
    after = c.now_ms()
    assert after-before == pytest.approx(999, abs=.01)
    monkeypatch.setattr(time, 'time', lambda: 0)
    assert c.now_ms() == after
    assert c.status()['source'] == 'local'


@pytest.mark.parametrize('available', [False, True])
def test_ntp_background_success_or_offline_fallback(monkeypatch, available):
    c = Clock()
    before = c.now_ms()
    monkeypatch.setenv('ROBOT_NTP_SERVER', 'test-clock')
    def probe(host):
        assert host == 'test-clock'
        if not available:
            raise OSError('offline')
        return 3600.
    async def finish(seconds):
        assert seconds == 300
        raise asyncio.CancelledError
    monkeypatch.setattr(c, 'probe', probe)
    monkeypatch.setattr(asyncio, 'sleep', finish)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(c.run())
    assert c.source == ('ntp' if available else 'local')
    assert c.target == (3600 if available else 0)
    assert bool(c.ntp_error) != available
    assert 0 <= c.now_ms()-before < 1000  # NTP never jumps the shared timeline


def test_ntp_wire_exchange_and_response_validation(monkeypatch):
    c = Clock()
    epoch = 1_800_000_000
    c.origin = epoch-100
    monkeypatch.setattr(time, 'time', lambda: epoch)
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: [(socket.AF_INET, socket.SOCK_DGRAM, 0, '', ('127.0.0.1', 123))])
    class Socket:
        bad_echo = False
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def settimeout(self, timeout): assert timeout == 1
        def connect(self, address): assert address == ('127.0.0.1', 123)
        def send(self, request): self.request = request
        def recv(self, size):
            response = bytearray(48)
            response[0], response[1] = 0x24, 1
            response[24:32] = bytes(8) if self.bad_echo else self.request[40:48]
            for index, value in [(32, epoch+.009), (40, epoch+.011)]:
                response[index:index+8] = struct.pack('!Q', int((value+2208988800)*2**32))
            return response
    for bad_echo in [False, True]:
        sample = Socket()
        sample.bad_echo = bad_echo
        monkeypatch.setattr(socket, 'socket', lambda *args: sample)
        ticks = iter([100., 100.020])
        monkeypatch.setattr(time, 'monotonic', lambda: next(ticks))
        if bad_echo:
            with pytest.raises(OSError, match='NTP unavailable'):
                c.probe('clock')
        else:
            assert c.probe('clock') == pytest.approx(0, abs=.00001)


def test_device_sync_does_not_bind_or_change_motion():
    fleet = Fleet(default_settings(), 'hardware')
    protocol = DeviceProtocol(fleet)
    sent = []
    protocol.send = lambda payload, addr: sent.append(payload)
    protocol.datagram_received(b'{"type":"time_sync","id":1,"t1":12.5}', ('127.0.0.1', 9998))
    assert sent[0]['t3'] >= sent[0]['t2']
    assert sent[0]['t1'] == 12.5
    assert not fleet.robot('car-01').bound
    protocol.datagram_received(b'[]', ('127.0.0.1', 9998))
    assert protocol.rejected == 1


def test_websocket_sync_and_disconnect_release(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import create_app
    monkeypatch.setenv('ROBOT_NTP_SERVER', '')
    with TestClient(create_app(db_path=tmp_path/'config.db')) as client:
        client.headers['X-Control-ID'] = 'clock-owner'
        assert client.post('/api/robots/car-01/arm', json={'enabled': True}).status_code == 200
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'time_sync', 't1': 123})
            while (reply := ws.receive_json()).get('type') != 'time_sync':
                pass
            assert reply['t1'] == 123 and reply['t3'] >= reply['t2']
            ws.send_json({'type': 'control', 'owner': 'clock-owner', 'seq': 1,
                          'robot_id': 'car-01', 'command': {'v': .05, 'omega': 0}})
            while (reply := ws.receive_json()).get('type') != 'control_ack':
                pass
            assert reply['packet']['v'] == .05
        assert not client.get('/api/state').json()['robots'][0]['armed']
        assert client.get('/api/time').json()['source'] == 'local'


def test_schedule_requires_sync_and_rejects_late_commands():
    from backend.clock import clock
    from backend.models import Command
    fleet = Fleet(default_settings(), 'hardware')
    fleet.allow_unlocalized_control = True
    r = fleet.robot('car-01')
    r.seen_at = time.monotonic()
    r.bound = r.armed = True
    r.owner = 'owner'
    r.endpoint = ('127.0.0.1', 9998)
    r.telemetry_seq = 1
    r.boot_id = 'test'
    with pytest.raises(ValueError, match='同步'):
        fleet.command(r, Command(v=.05, omega=0, execute_at_ms=clock.now_ms()+100), 'owner')
    r.bound = r.armed = r.clock_synced = True
    r.owner = 'owner'
    deadline = clock.now_ms()+100
    packet = fleet.command(r, Command(v=.05, omega=0, execute_at_ms=deadline), 'owner')
    assert packet['execute_at_ms'] == deadline
    with pytest.raises(ValueError, match='过期'):
        fleet.command(r, Command(v=.05, omega=0, execute_at_ms=clock.now_ms()-1), 'owner')
    assert not r.armed
