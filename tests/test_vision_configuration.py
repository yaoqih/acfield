import copy
import json
import threading
import time

import pytest

import apriltag_live
from apriltag_live import ROOT, DemoSource, LiveEngine, create_app, load_settings


def wait_until(check, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if result := check():
            return result
        time.sleep(.025)
    raise AssertionError('capture worker timed out')


@pytest.fixture
def engine(tmp_path, monkeypatch):
    demo = DemoSource(load_settings(ROOT/'apriltag_live.json'))
    _, image = demo.read()
    class FakeCapture:
        def __init__(self, index):
            self.open = index in (0, 2)
        def isOpened(self):
            return self.open
        def set(self, *args):
            return True
        def read(self):
            return self.open, image.copy() if self.open else None
        def release(self):
            self.open = False
    monkeypatch.setattr(apriltag_live.cv2, 'VideoCapture', FakeCapture)
    engine = LiveEngine(demo.config, backend='opencv', width=1440, height=1000,
                        runtime_path=tmp_path/'vision-settings.json')
    engine.start()
    wait_until(lambda: engine.snapshot().get('status') == 'running')
    try:
        yield engine
    finally:
        engine.stop()


def test_camera_config_persistence_scan_disconnect_and_failure(engine):
    client = create_app(engine).test_client()
    devices = client.post('/api/cameras', json={})
    assert devices.status_code == 200
    assert [d['id'] for d in devices.json['cameras']] == ['0', '2']
    profile = client.get('/api/config').json['config']
    profile.update(source='2', enabled=True)
    result = client.post('/api/config', json=profile)
    assert result.status_code == 200, result.json
    wait_until(lambda: engine.snapshot().get('source_kind') == 'camera')
    persisted = json.loads(engine.runtime_path.read_text())['profile']
    assert persisted['source'] == '2' and persisted['enabled']
    bad = {**profile, 'source': '9'}
    result = client.post('/api/config', json=bad)
    assert result.status_code == 400 and '无法打开' in result.json['error']
    assert engine.source_name == '2'
    assert json.loads(engine.runtime_path.read_text())['profile']['source'] == '2'
    result = client.post('/api/config', json={**profile, 'enabled': False})
    assert result.status_code == 200 and engine.capture is None
    assert not json.loads(engine.runtime_path.read_text())['profile']['enabled']


def test_calibration_roundtrip_requires_current_fixed_tags_and_resets_on_config(engine):
    client = create_app(engine).test_client()
    profile = client.get('/api/config').json['config']
    profile.update(source='0', enabled=True)
    assert client.post('/api/config', json=profile).status_code == 200
    wait_until(lambda: engine.snapshot().get('source_kind') == 'camera')
    response = client.post('/api/operations', json={'action': 'calibrate'})
    assert response.status_code == 200, response.json
    wait_until(lambda: engine.snapshot().get('world_calibrated'))
    assert json.loads(engine.runtime_path.read_text())['saved_world']['info']['rms_px'] < 1
    # Reconnecting an unchanged camera profile keeps a manually loadable calibration.
    assert client.post('/api/config', json=profile).status_code == 200
    wait_until(lambda: engine.latest_acquired is not None)
    assert not engine.snapshot().get('world_calibrated')
    response = client.post('/api/operations', json={'action': 'load_world'})
    assert response.status_code == 200, response.json
    wait_until(lambda: engine.snapshot().get('world_calibrated'))
    profile['tags']['10']['size_m'] = .15
    assert client.post('/api/config', json=profile).status_code == 200
    assert engine.saved_world is None and engine.extrinsic is None
    assert client.post('/api/operations', json={'action': 'load_world'}).status_code == 400


@pytest.mark.parametrize('change', [
    {'source': 'http://example.com'}, {'fps': float('nan')}, {'width': True},
    {'family': 'tag16h5'}, {'tags': {}}, {'camera': {'camera_matrix': []}},
])
def test_invalid_profiles_never_replace_working_capture(engine, change):
    client = create_app(engine).test_client()
    original = engine.capture
    payload = {**client.get('/api/config').json['config'], **change}
    assert client.post('/api/config', json=payload).status_code == 400
    assert engine.capture is original
    assert not engine.runtime_path.exists()


def test_real_http_bridge_synchronizes_robot_dimensions(engine, tmp_path):
    pytest.importorskip('fastapi')
    from fastapi.testclient import TestClient
    from werkzeug.serving import make_server
    from robot_server.backend.app import create_app as control_app
    server = make_server('127.0.0.1', 0, create_app(engine), threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        app = control_app(mode='hardware', udp_port=0, db_path=tmp_path/'control.db')
        with TestClient(app) as client:
            settings = client.get('/api/config').json()
            settings['vision_url'] = f'http://127.0.0.1:{server.server_port}'
            settings['vision'] = engine.configuration()
            settings['vision'].pop('saved_world')
            settings['vision'].update(source='0', enabled=True)
            settings['robots'][0].update(tag_size=.13, tag_height=.09)
            response = client.put('/api/config', json=settings)
            assert response.status_code == 200, response.json()
            assert engine.settings['tags']['10']['size_m'] == .13
            assert engine.settings['tags']['10']['height_m'] == .09
            wait_until(lambda: client.get('/api/state').json()['camera'].get('available'))
            assert not client.get('/api/state').json()['camera']['connected']
            assert client.post('/api/vision/operations', json={'action': 'calibrate'}).status_code == 200
            wait_until(lambda: client.get('/api/state').json()['camera']['connected'])
            assert client.get('/api/state').json()['estop']
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)
