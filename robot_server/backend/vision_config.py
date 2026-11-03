"""Camera profile contract and HTTP bridge to the capture service."""
from typing import Literal

import httpx
from fastapi import HTTPException
from pydantic import Field

from .models import Model, Settings


class CameraProfile(Model):
    source: str = Field(pattern=r'^(?:[0-9]|[1-5][0-9]|6[0-3])$')
    enabled: bool
    width: int = Field(ge=16, le=8192)
    height: int = Field(ge=16, le=8192)
    fps: float = Field(ge=1, le=120)
    family: Literal['tag36h11'] = 'tag36h11'
    decimate: float = Field(default=1, ge=1, le=4)
    camera: dict | None = None
    tags: dict[str, dict] = Field(min_length=4, max_length=128)
    world: dict


class ConfigurationRequest(Settings):
    vision: CameraProfile | None = None


class VisionAction(Model):
    action: Literal['calibrate', 'reset_world', 'load_world']


async def request_vision(url, method, path, body=None):
    if not url:
        raise HTTPException(409, '请先填写视觉服务地址，例如 http://127.0.0.1:8765')
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(25, connect=2)) as client:
            response = await client.request(method, url + path, json=body if body is not None else {})
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError('响应不是对象')
            if not response.is_success:
                raise HTTPException(502, str(data.get('error', '视觉服务操作失败')))
            if method == 'GET' and path == '/api/config':
                remote = dict(data.get('config', {}))
                remote.pop('saved_world', None)
                CameraProfile.model_validate(remote)
                if not isinstance(data.get('state'), dict):
                    raise ValueError('缺少视觉状态')
            return data
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, '无法连接视觉服务或接口版本不兼容，请启动更新后的 apriltag_live.py') from exc


def synchronize_profile(profile, settings, previous):
    """Use one physical size/height source; heading correction remains in Fleet."""
    profile = dict(profile)
    profile.pop('saved_world', None)
    profile['family'] = 'tag36h11'
    tags = {key: dict(value) for key, value in profile['tags'].items()}
    new_ids = {str(r.tag_id) for r in settings.robots}
    for old in previous.robots:
        key = str(old.tag_id)
        if key not in new_ids and tags.get(key, {}).get('role') != 'fixed':
            tags.pop(key, None)
    for robot in settings.robots:
        key = str(robot.tag_id)
        if robot.tag_id > 586:
            raise HTTPException(422, 'tag36h11 小车标签 ID 必须在 0–586 之间')
        if tags.get(key, {}).get('role') == 'fixed':
            raise HTTPException(422, f'小车标签 {key} 与场地固定标签重复')
        tags[key] = {**tags.get(key, {}), 'name': robot.name, 'role': 'robot',
                     'size_m': robot.tag_size, 'height_m': robot.tag_height, 'heading_offset_deg': 0}
        tags[key].pop('world_xyz_m', None)
    profile['tags'] = tags
    profile['world'] = {**profile['world'], 'boundary_xy_m': [
        [0, 0], [settings.arena_width, 0], [settings.arena_width, settings.arena_height], [0, settings.arena_height]]}
    return CameraProfile.model_validate(profile).model_dump()
