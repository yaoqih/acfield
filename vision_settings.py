"""Validated, persisted camera profiles shared by the dashboard and robot console."""
import copy
import json
import math
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np


def number(value, name, low, high, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} 必须是数字')
    if not math.isfinite(value) or not low <= value <= high or (integer and int(value) != value):
        raise ValueError(f'{name} 必须在 {low}–{high} 之间' + ('且为整数' if integer else ''))
    return int(value) if integer else float(value)


def validate_profile(payload):
    if not isinstance(payload, dict):
        raise ValueError('配置必须是 JSON 对象')
    profile = copy.deepcopy(payload)
    source = profile.get('source')
    if not isinstance(source, str) or not source.isascii() or not source.isdecimal():
        raise ValueError('相机 ID 必须是 0–63 的数字索引')
    profile['source'] = str(number(int(source), '相机 ID', 0, 63, True))
    if type(profile.get('enabled')) is not bool:
        raise ValueError('enabled 必须为布尔值')
    for key in ('width', 'height'):
        profile[key] = number(profile.get(key), key, 16, 8192, True)
    profile['fps'] = number(profile.get('fps'), '帧率', 1, 120)
    if profile.get('family') != 'tag36h11':
        raise ValueError('小车控制当前仅支持 tag36h11')
    profile['decimate'] = number(profile.get('decimate'), '检测降采样', 1, 4)
    camera = profile.get('camera')
    if camera is not None:
        try:
            k = np.asarray(camera['camera_matrix'], float)
            d = np.asarray(camera['dist_coeffs'], float)
            if (k.shape != (3, 3) or not np.isfinite(k).all() or k[0, 0] <= 0 or k[1, 1] <= 0
                    or not np.allclose(k[2], [0, 0, 1]) or d.ndim != 1
                    or len(d) not in (4, 5, 8, 12, 14) or not np.isfinite(d).all()):
                raise ValueError('相机内参或畸变参数无效')
            for key in ('image_width', 'image_height'):
                camera[key] = number(camera[key], key, 16, 16384, True)
        except (KeyError, TypeError) as exc:
            raise ValueError('相机内参字段不完整') from exc
    tags = profile.get('tags')
    if not isinstance(tags, dict) or not 4 <= len(tags) <= 128:
        raise ValueError('需要配置 4–128 个标签')
    fixed = []
    for key, spec in tags.items():
        if not key.isascii() or not key.isdecimal() or str(int(key)) != key or not 0 <= int(key) <= 586:
            raise ValueError('tag36h11 标签 ID 必须在 0–586 之间')
        if not isinstance(spec, dict):
            raise ValueError('标签配置无效')
        number(spec.get('size_m'), '标签黑框边长', .005, 1)
        number(spec.get('height_m', 0), '标签安装高度', 0, 10)
        number(spec.get('heading_offset_deg', 0), '标签航向修正', -360, 360)
        if spec.get('role') == 'fixed':
            xyz = np.asarray(spec.get('world_xyz_m'), float)
            if xyz.shape != (3,) or not np.isfinite(xyz).all() or xyz[2] != 0:
                raise ValueError('固定标签需要有限的地面坐标 [x, y, 0]')
            fixed.append(xyz)
    if len(fixed) < 4 or np.linalg.matrix_rank(np.array(fixed)[:, :2] - fixed[0][:2]) < 2:
        raise ValueError('需要至少四个不共线的固定标签')
    world = profile.get('world')
    boundary = np.asarray(world.get('boundary_xy_m') if isinstance(world, dict) else None, float)
    if boundary.shape != (4, 2) or not np.isfinite(boundary).all() or type(world.get('configured')) is not bool:
        raise ValueError('场地边界和坐标确认状态无效')
    return {key: profile[key] for key in ('source', 'enabled', 'width', 'height', 'fps',
                                         'family', 'decimate', 'camera', 'tags', 'world')}


def save_runtime(path, data):
    """Atomic replacement; never overwrite the hand-edited apriltag_live.json."""
    if path is None:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def discover_cameras(current_source, capture, limit=6):
    """Probe only on explicit refresh, on the capture worker, never while reading."""
    devices = []
    for index in range(limit):
        if capture is not None and str(index) == current_source:
            devices.append({'id': str(index), 'name': f'相机 {index}（当前连接）'})
            continue
        probe = cv2.VideoCapture(index)
        try:
            if probe.isOpened():
                name_file = Path(f'/sys/class/video4linux/video{index}/name')
                name = name_file.read_text().strip() if name_file.is_file() else f'相机 {index}'
                devices.append({'id': str(index), 'name': name})
        finally:
            probe.release()
    return devices
