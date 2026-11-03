import asyncio
import contextlib
import copy
import time

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.models import default_settings
from backend.state import Fleet
from backend.vision import ingest, watch


def profile():
    return {'source': '2', 'enabled': True, 'width': 1280, 'height': 720, 'fps': 30,
            'family': 'tag36h11', 'decimate': 1, 'camera': None,
            'world': {'configured': False, 'boundary_xy_m': [[0, 0], [3, 0], [3, 3], [0, 3]]},
            'tags': {str(i): {'name': str(i), 'role': 'fixed', 'size_m': .104,
                             'height_m': 0, 'world_xyz_m': xyz}
                     for i, xyz in enumerate([[0, 0, 0], [3, 0, 0], [3, 3, 0], [0, 3, 0]])}}


async def idle_watch(*args):
    await asyncio.Future()


def test_save_synchronizes_physics_and_persists_url(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.app.watch', idle_watch)
    calls = []
    async def remote(url, method, path, body=None):
        if method == 'GET':
            return {'config': profile()}
        calls.append((url, body))
        fleet = app.state.fleet
        assert fleet.estop and fleet.vision_updating
        fleet.estop = False  # Another client releasing stop cannot bypass configuration guard.
        assert '更新' in fleet.ready(fleet.robot('car-01'), time.monotonic())
        return body
    monkeypatch.setattr('backend.app.request_vision', remote)
    path = tmp_path/'config.db'
    app = create_app(mode='hardware', db_path=path, udp_port=0)
    with TestClient(app) as client:
        settings = client.get('/api/config').json()
        settings['vision_url'] = 'http://camera:8765/'
        settings['robots'][0].update(tag_size=.15, tag_height=.08, heading_offset=1.2)
        assert client.put('/api/config', json=settings).status_code == 200
        url, sent = calls[-1]
        assert url == 'http://camera:8765'
        assert sent['tags']['10']['size_m'] == .15
        assert sent['tags']['10']['height_m'] == .08
        assert sent['tags']['10']['heading_offset_deg'] == 0
        assert client.get('/api/state').json()['estop']
        assert all(not r['armed'] for r in client.get('/api/state').json()['robots'])
    with TestClient(create_app(mode='hardware', db_path=path, udp_port=0)) as client:
        assert client.get('/api/config').json()['vision_url'] == 'http://camera:8765'


def test_failed_sync_retains_settings_and_blocks_motion_until_retry(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.app.watch', idle_watch)
    failed = True
    async def remote(url, method, path, body=None):
        if failed:
            raise HTTPException(502, '无法打开相机 9')
        return body
    monkeypatch.setattr('backend.app.request_vision', remote)
    app = create_app(mode='hardware', db_path=tmp_path/'config.db', udp_port=0)
    with TestClient(app) as client:
        original = client.get('/api/config').json()
        settings = {**original, 'vision_url': 'http://camera:8765', 'vision': profile()}
        response = client.put('/api/config', json=settings)
        assert response.status_code == 502 and '相机 9' in response.json()['detail']
        assert client.get('/api/config').json() == original
        assert client.get('/api/state').json()['estop']
        client.post('/api/reset-stop')
        assert '同步失败' in app.state.fleet.ready(app.state.fleet.robot('car-01'), time.monotonic())
        failed = False
        assert client.put('/api/config', json=settings).status_code == 200
        assert app.state.fleet.vision_sync_error is None


def test_failed_camera_operation_keeps_motion_blocked_until_profile_resync(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.app.watch', idle_watch)
    async def remote(url, method, path, body=None):
        if path == '/api/operations':
            raise HTTPException(502, '视觉服务操作失败')
        return body
    monkeypatch.setattr('backend.app.request_vision', remote)
    app = create_app(mode='hardware', db_path=tmp_path/'config.db', udp_port=0)
    with TestClient(app) as client:
        settings = client.get('/api/config').json()
        settings.update(vision_url='http://camera:8765', vision=profile())
        assert client.put('/api/config', json=settings).status_code == 200
        assert client.post('/api/vision/operations', json={'action': 'calibrate'}).status_code == 502
        fleet = app.state.fleet
        assert fleet.vision_sync_error
        client.post('/api/reset-stop')
        assert '不确定' in fleet.ready(fleet.robot('car-01'), time.monotonic())
        retry = client.get('/api/config').json()
        retry['vision'] = profile()
        assert client.put('/api/config', json=retry).status_code == 200
        assert app.state.fleet.vision_sync_error is None


def test_concurrent_config_write_cannot_rearm_during_vision_change(tmp_path, monkeypatch):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        async def remote(url, method, path, body=None):
            entered.set()
            await release.wait()
            return body or {'config': profile()}
        monkeypatch.setattr('backend.app.request_vision', remote)
        app = create_app(mode='hardware', db_path=tmp_path/'config.db', udp_port=0)
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url='http://test',
                                         headers={'X-Control-ID': 'camera-test'}) as client:
                settings = (await client.get('/api/config')).json()
                settings['vision_url'] = 'http://camera:8765'
                settings['vision'] = profile()
                fleet = app.state.fleet
                robot = fleet.robot('car-01')
                robot.seen_at = time.monotonic()
                robot.bound = True
                fleet.pose(robot, 1, 1, 0, time.monotonic())
                write = asyncio.create_task(client.put('/api/config', json=settings))
                await asyncio.wait_for(entered.wait(), 2)
                await client.post('/api/reset-stop')
                blocked = await client.post('/api/robots/car-01/arm', json={'enabled': True})
                assert blocked.status_code == 409 and '更新' in blocked.json()['detail']
                release.set()
                assert (await asyncio.wait_for(write, 3)).status_code == 200
                assert fleet.vision_sync_error is None
    asyncio.run(scenario())


def test_conflicting_fixed_id_and_demo_camera_operations_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.app.watch', idle_watch)
    with TestClient(create_app(mode='hardware', db_path=tmp_path/'hardware.db', udp_port=0)) as client:
        settings = client.get('/api/config').json()
        settings.update(vision_url='http://camera:8765', vision=profile())
        settings['robots'][0]['tag_id'] = 0
        assert client.put('/api/config', json=settings).status_code == 422
    with TestClient(create_app(db_path=tmp_path/'demo.db')) as client:
        assert client.post('/api/vision/cameras', json={}).status_code == 409
        assert client.post('/api/vision/operations', json={'action': 'calibrate'}).status_code == 409
        assert client.get('/api/vision/config?url=file:///etc/passwd').status_code == 422


def test_uncalibrated_camera_can_preview_without_usable_pose():
    fleet = Fleet(default_settings(), 'hardware')
    ingest(fleet, {'status': 'running', 'demo': False, 'source_kind': 'camera',
                  'world_calibrated': False, 'frame_age_ms': 10, 'fps': 25}, time.monotonic(), None)
    assert fleet.camera['available'] and not fleet.camera['connected']
    assert all(r.pose_at == 0 for r in fleet.robots.values())


def test_watcher_discards_inflight_frames_and_follows_url_changes(monkeypatch):
    async def scenario():
        fleet = Fleet(default_settings(), 'hardware')
        url = 'http://old'
        started, release, next_started = asyncio.Event(), asyncio.Event(), asyncio.Event()
        frame = {'status': 'running', 'demo': False, 'source_kind': 'camera',
                 'world_calibrated': True, 'family': 'tag36h11', 'timestamp_utc': 'now',
                 'frame_id': 1, 'frame_age_ms': 0, 'tags': [
                     {'id': 10, 'status': 'visible', 'world_xyz_m': [1, 1, .08],
                      'heading_world_deg': 0, 'age_ms': 0}]}
        async def reply(request):
            if request.url.host == 'old':
                started.set()
                await release.wait()
            else:
                next_started.set()
                await asyncio.Future()
            return httpx.Response(200, json=frame)
        original = httpx.AsyncClient
        monkeypatch.setattr('backend.vision.httpx.AsyncClient', lambda **kw: original(transport=httpx.MockTransport(reply)))
        task = asyncio.create_task(watch(fleet, lambda: url))
        try:
            await asyncio.wait_for(started.wait(), 1)
            url = 'http://new'
            fleet.vision_revision += 1
            release.set()
            await asyncio.wait_for(next_started.wait(), 1)
            assert fleet.robot('car-01').pose_at == 0
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
    asyncio.run(scenario())
