import json
import math
import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from apriltag_live import (ROOT, DemoSource, Detector, LiveEngine, Tracker,
                           calibrate_world, camera_at_size, create_app,
                           estimate_pose, load_settings, ray_to_plane, square_points)


@pytest.fixture(scope='module')
def scene():
    source = DemoSource(load_settings(ROOT/'apriltag_live.json'))
    _, image = source.read()
    camera = camera_at_size(source.config['camera'], source.width, source.height)
    return source, image, camera


@pytest.mark.parametrize('backend', ['native', 'opencv'])
def test_both_backends_decode_same_canonical_corners_at_all_rotations(backend):
    if backend == 'native':
        pytest.importorskip('pupil_apriltags')
    detector = Detector(backend=backend)
    for tag_id in [0, 1, 2, 3, 10, 11, 12, 13]:
        image = cv2.imread(str(ROOT/f'output/apriltags/tag36h11_id{tag_id:03d}_{"fixed" if tag_id < 4 else "robot"}.png'), 0)
        image = cv2.resize(image, (400, 400), interpolation=cv2.INTER_NEAREST)
        original = np.array([[40., 40.], [359., 40.], [359., 359.], [40., 359.]])
        for rotation in range(4):
            rotated = np.rot90(image, rotation).copy()
            found = detector.detect(rotated)
            assert [t['id'] for t in found] == [tag_id]
            expected = original.copy()
            for _ in range(rotation):
                expected = np.column_stack([expected[:, 1], 399 - expected[:, 0]])
            assert np.max(np.abs(found[0]['corners'] - expected)) < 2


def test_oblique_scene_calibrates_and_corrects_roof_height(scene):
    source, image, camera = scene
    found = Detector().detect(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    assert {t['id'] for t in found} == {0, 1, 2, 3, 10, 11, 12, 13}
    extrinsic, info = calibrate_world(found, source.config['tags'], camera)
    assert info['rms_px'] < .5
    assert np.linalg.norm(extrinsic[0] - source.rotation) < .02
    world = np.array([2.1, 2.5, .12])
    pixel = source.project([world])[0]
    corrected = ray_to_plane(pixel, .12, camera, extrinsic)
    wrong = ray_to_plane(pixel, 0., camera, extrinsic)
    assert np.linalg.norm(corrected - world) < .02
    assert np.linalg.norm(wrong[:2] - world[:2]) > .1
    with pytest.raises(ValueError, match='四个'):
        calibrate_world([t for t in found if t['id'] != 2], source.config['tags'], camera)


def test_ippe_pose_matches_known_camera_translation(scene):
    source, _, camera = scene
    center = np.array([1.8, 1.2, .12])
    points = square_points(.12) + center
    corners = source.project(points)
    pose = estimate_pose(corners, .12, camera)
    expected = source.rotation @ center + source.translation
    assert np.linalg.norm(np.array(pose['camera_xyz_m']) - expected) < 1e-5
    assert pose['reprojection_rms_px'] < 1e-5
    assert estimate_pose(corners, .12, None) is None
    assert estimate_pose(corners, None, camera) is None


def test_resolution_and_calibration_guards(scene):
    source, _, _ = scene
    scaled = camera_at_size(source.config['camera'], 720, 500)
    assert scaled[0][0, 0] == 710
    with pytest.raises(ValueError, match='aspect ratio'):
        camera_at_size(source.config['camera'], 1280, 720)
    assert camera_at_size(None, 1280, 720) is None


def test_family_mismatch_does_not_reuse_physical_dimensions():
    engine = LiveEngine(load_settings(ROOT/'apriltag_live.json'))
    assert len(engine.tag_specs()) == 8
    engine.family = 'tag16h5'
    assert engine.tag_specs() == {}


def test_api_marks_frozen_capture_as_lost():
    engine = LiveEngine(load_settings(ROOT/'apriltag_live.json'))
    engine.state = {'tags':[{'id':10, 'age_ms':0., 'status':'visible'}],
                    'tag_age_reference_monotonic':time.monotonic()-1,
                    'acquired_monotonic':time.monotonic()-1}
    result = engine.snapshot()
    assert result['tags'][0]['status'] == 'lost'
    assert result['tags'][0]['age_ms'] >= 1000
    assert result['frame_age_ms'] >= 1000


def test_lost_tracks_never_invent_velocity_on_reappearance():
    tracker = Tracker()
    def detection(x):
        return {'id': 10, 'center': np.array([x, 100.]),
                'corners': np.array([[x-10, 90], [x+10, 90], [x+10, 110], [x-10, 110]], float),
                'margin': 50., 'hamming': 0}
    specs = {'10': {'size_m': .12, 'role': 'pursuer', 'height_m': .12}}
    result = tracker.update([detection(100)], 100., None, None, specs)[0]
    assert result['speed_px_s'] is None and result['world_xyz_m'] is None
    result = tracker.update([detection(110)], 100.1, None, None, specs)[0]
    assert result['speed_px_s'] == pytest.approx(100)
    result = tracker.update([], 101., None, None, specs)[0]
    assert result['status'] == 'lost' and result['age_ms'] == pytest.approx(900)
    result = tracker.update([detection(200)], 102., None, None, specs)[0]
    assert result['speed_px_s'] is None


def wait_until(check, timeout=5):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(.025)
    raise AssertionError('Timed out waiting for capture worker')


def test_camera_movement_invalidates_world_calibration(monkeypatch):
    import apriltag_live
    class ShiftableDemo(DemoSource):
        shift_px = 0
        def read(self):
            ok, image = super().read()
            if self.shift_px:
                image = cv2.warpAffine(image, np.float32([[1, 0, self.shift_px], [0, 1, 0]]),
                                       (self.width, self.height), borderValue=(29, 36, 44))
            return ok, image
    monkeypatch.setattr(apriltag_live, 'DemoSource', ShiftableDemo)
    engine = LiveEngine(load_settings(ROOT/'apriltag_live.json'))
    engine.start()
    try:
        wait_until(lambda: engine.snapshot().get('visible_count') == 8)
        engine.command({'action':'calibrate'})
        wait_until(lambda: engine.snapshot().get('world_calibrated'))
        ShiftableDemo.shift_px = 25
        wait_until(lambda: not engine.snapshot().get('world_calibrated'))
        assert any('已清除场地外参' in e['text'] for e in engine.snapshot()['events'])
        assert all(t['world_xyz_m'] is None for t in engine.snapshot()['tags'])
    finally:
        engine.stop()


def test_live_api_calibration_exports_recording_and_input_recovery(tmp_path):
    engine = LiveEngine(load_settings(ROOT/'apriltag_live.json'))
    app = create_app(engine)
    client = app.test_client()
    engine.start()
    try:
        wait_until(lambda: engine.snapshot().get('visible_count') == 8)
        assert client.get('/').status_code == 200
        assert client.get('/assets/app.js').status_code == 200
        assert client.get('/api/snapshot.jpg').data.startswith(b'\xff\xd8')
        assert client.get('/api/export.csv').data.startswith(b'\xef\xbb\xbf')
        assert len(client.get('/api/export.json').json['tags']) == 8
        assert client.post('/api/control', json={'action': 'calibrate'}, headers={'Origin':'http://elsewhere.example'}).status_code == 403
        for payload in [None, {}, {'action':'nonsense'}, {'action':'detector','decimate':float('nan')}, {'action':'source','source':123}]:
            assert client.post('/api/control',json=payload).status_code in (400,415)
        assert client.post('/api/control',json={'action':'calibrate'}).status_code == 202
        wait_until(lambda: engine.snapshot().get('world_calibrated'))
        calibrated = engine.snapshot()
        assert all(t['world_xyz_m'] is not None for t in calibrated['tags'])
        # A failed source switch must keep the working source available.
        engine.command({'action':'source','source':str(tmp_path/'missing.mp4')})
        wait_until(lambda: any('不存在' in e['text'] for e in engine.snapshot()['events']))
        assert engine.snapshot()['source'] == 'demo'
        engine.command({'action':'record'})
        wait_until(lambda: engine.snapshot().get('recording'))
        with engine.lock:
            folder = engine.record['folder']
        wait_until(lambda: engine.record and engine.record['frames'] >= 2)
        engine.command({'action':'record'})
        wait_until(lambda: engine.record is None)
        rows = [json.loads(line) for line in (folder/'frames.jsonl').read_text().splitlines()]
        assert len(rows) >= 2 and all(r['demo'] for r in rows)
        assert all(len(r['tags']) == 8 for r in rows)
        assert 'history' not in rows[0]['tags'][0]
        assert json.loads((folder/'config.json').read_text())['extrinsic_world_to_camera'] is not None
        # Clean this test's generated recording only.
        for path in folder.iterdir():
            path.unlink()
        folder.rmdir()
    finally:
        engine.stop()
