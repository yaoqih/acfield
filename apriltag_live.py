#!/usr/bin/env python3
"""Local AprilTag dashboard: python3 apriltag_live.py --source demo.

The demo renders real tag patterns and runs the same detector as the camera.
It sends no robot commands. Coordinates are tag centres, not axle centres.
"""
from __future__ import annotations

import argparse
import copy
import csv
import io
import json
import math
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, Response, jsonify, request, send_file
from vision_settings import discover_cameras, save_runtime, validate_profile

ROOT = Path(__file__).resolve().parent
NATIVE_FAMILIES = ['tag36h11', 'tag16h5', 'tag25h9', 'tagStandard41h12',
                   'tagStandard52h13', 'tagCircle21h7', 'tagCircle49h12', 'tagCustom48h12']
COLORS = [(65, 207, 128), (76, 190, 250), (227, 155, 93), (195, 132, 234)]


def finite_number(value, name, low, high):
    if isinstance(value, bool):
        raise ValueError(f'{name} must be a number')
    number = float(value)
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError(f'{name} must be between {low} and {high}')
    return number


def load_settings(path):
    config = json.loads(Path(path).read_text(encoding='utf-8'))
    config.setdefault('camera', None)
    config.setdefault('family', 'tag36h11')
    config.setdefault('world', {'configured': False})
    config.setdefault('tags', {})
    for key, spec in config['tags'].items():
        int(key)
        finite_number(spec['size_m'], 'size_m', .005, 5)
        finite_number(spec.get('height_m', 0), 'height_m', 0, 10)
        if spec.get('world_xyz_m') is not None:
            xyz = np.asarray(spec['world_xyz_m'], dtype=float)
            if xyz.shape != (3,) or not np.isfinite(xyz).all():
                raise ValueError(f'Invalid world_xyz_m for tag {key}')
    camera = config['camera']
    if camera is not None:
        k = np.asarray(camera['camera_matrix'], dtype=float)
        d = np.asarray(camera['dist_coeffs'], dtype=float).reshape(-1)
        if (k.shape != (3, 3) or not np.isfinite(k).all() or k[0, 0] <= 0
                or k[1, 1] <= 0 or not np.allclose(k[2], [0, 0, 1])
                or len(d) not in (4, 5, 8, 12, 14) or not np.isfinite(d).all()):
            raise ValueError('Invalid OpenCV camera calibration')
        for name in ('image_width', 'image_height'):
            finite_number(camera[name], name, 16, 16384)
    return config


class Detector:
    def __init__(self, family='tag36h11', decimate=1.0, backend='auto'):
        self.family = family
        self.native = None
        if backend != 'opencv':
            try:
                from native_apriltag import Detector as NativeDetector
                if family not in NATIVE_FAMILIES:
                    raise ValueError(f'Unsupported native family: {family}')
                self.native = NativeDetector(families=family, nthreads=2,
                                             quad_decimate=decimate, refine_edges=1)
            except ImportError:
                if backend == 'native':
                    raise RuntimeError('Install pupil-apriltags for the AprilTag 3 backend')
        if self.native is not None:
            self.name = 'AprilTag 3 / pupil-apriltags'
            self.families = NATIVE_FAMILIES
        else:
            # Only this fallback convention is covered by rotation tests.
            if family != 'tag36h11':
                raise ValueError('OpenCV fallback supports tag36h11 here; install pupil-apriltags for other families')
            if not hasattr(cv2, 'aruco'):
                raise RuntimeError('Install opencv-contrib-python >= 4.8')
            params = cv2.aruco.DetectorParameters()
            params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
            self.cv = cv2.aruco.ArucoDetector(
                cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11), params)
            self.name = 'OpenCV / AprilTag dictionary (fallback)'
            self.families = ['tag36h11']

    def detect(self, gray):
        if self.native is not None:
            return [{'id': int(t.tag_id), 'center': t.center,
                     # Canonical printed top-left, top-right, bottom-right, bottom-left.
                     'corners': t.corners[[3, 2, 1, 0]],
                     'margin': float(t.decision_margin), 'hamming': int(t.hamming)}
                    for t in self.native.detect(np.ascontiguousarray(gray))]
        corners, ids, _ = self.cv.detectMarkers(gray)
        if ids is None:
            return []
        def projective_center(points):
            h = cv2.getPerspectiveTransform(np.array([[0, 0], [1, 0], [1, 1], [0, 1]], np.float32), points.astype(np.float32))
            return cv2.perspectiveTransform(np.array([[[.5, .5]]], np.float32), h).reshape(2)
        return [{'id': int(i), 'center': projective_center(c[0]),
                 'corners': c[0][[2, 3, 0, 1]].astype(float),
                 'margin': None, 'hamming': None} for c, i in zip(corners, ids.flat)]


def camera_at_size(camera, width, height):
    if camera is None:
        return None
    # Only uniform full-frame scaling is supported; cropping needs recalibration.
    sx, sy = width / camera['image_width'], height / camera['image_height']
    if abs(sx / sy - 1) > .005:
        raise ValueError('Resolution aspect ratio differs from calibration; use the calibrated camera mode')
    k = np.asarray(camera['camera_matrix'], dtype=float).copy()
    k[0] *= sx
    k[1] *= sy
    return k, np.asarray(camera['dist_coeffs'], dtype=float)


def square_points(size):
    s = size / 2
    return np.array([[-s, s, 0], [s, s, 0], [s, -s, 0], [-s, -s, 0]], float)


def estimate_pose(corners, size, camera):
    if camera is None or size is None:
        return None
    k, d = camera
    objects = square_points(size)
    result = cv2.solvePnPGeneric(objects, np.asarray(corners, float), k, d,
                                 flags=cv2.SOLVEPNP_IPPE_SQUARE)
    candidates = []
    for rv, tv in zip(result[1], result[2]):
        rotation = cv2.Rodrigues(rv)[0]
        if np.min((rotation @ objects.T + tv).T[:, 2]) <= 0:
            continue
        projected = cv2.projectPoints(objects, rv, tv, k, d)[0].reshape(-1, 2)
        error = float(np.sqrt(np.mean(np.sum((projected - corners) ** 2, axis=1))))
        candidates.append((error, rv, tv, rotation))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p[0])
    error, rv, tv, rotation = candidates[0]
    alt = candidates[1][0] if len(candidates) > 1 else None
    # ZYX convention: R = Rz(yaw) @ Ry(pitch) @ Rx(roll), tag -> OpenCV camera.
    roll = math.atan2(rotation[2, 1], rotation[2, 2])
    pitch = math.atan2(-rotation[2, 0], math.hypot(rotation[2, 1], rotation[2, 2]))
    yaw = math.atan2(rotation[1, 0], rotation[0, 0])
    return {'camera_xyz_m': tv.reshape(3).tolist(), 'range_m': float(np.linalg.norm(tv)),
            'rvec_rad': rv.reshape(3).tolist(), 'rotation_matrix': rotation.tolist(),
            'rpy_deg': np.degrees([roll, pitch, yaw]).tolist(),
            'reprojection_rms_px': error, 'alternative_rms_px': alt,
            'ambiguous': alt is not None and alt - error < .25,
            'tilt_deg': math.degrees(math.acos(float(np.clip(abs(rotation[2, 2]), 0, 1))))}


def ray_to_plane(pixel, z, camera, extrinsic):
    if camera is None or extrinsic is None:
        return None
    k, d = camera
    uv = cv2.undistortPoints(np.asarray(pixel, float).reshape(1, 1, 2), k, d).reshape(2)
    rotation, translation = extrinsic
    origin = -rotation.T @ translation.reshape(3)
    direction = rotation.T @ np.array([uv[0], uv[1], 1.0])
    if abs(direction[2]) < 1e-9:
        return None
    scale = (z - origin[2]) / direction[2]
    if scale <= 0:
        return None
    return origin + scale * direction


def calibrate_world(detections, tags, camera):
    if camera is None:
        raise ValueError('先填写相机内参与畸变参数')
    by_id = {t['id']: t for t in detections}
    specs = [(int(i), s) for i, s in tags.items()
             if s.get('role') == 'fixed' and s.get('world_xyz_m') is not None]
    if len(specs) < 4 or any(i not in by_id for i, _ in specs):
        raise ValueError('需要同时看见至少四个已配置坐标的固定标签')
    objects = np.asarray([s['world_xyz_m'] for _, s in specs], float)
    pixels = np.asarray([by_id[i]['center'] for i, _ in specs], float)
    if not np.allclose(objects[:, 2], 0) or np.linalg.matrix_rank(objects[:, :2] - objects[0, :2]) < 2:
        raise ValueError('固定标签中心必须在地面 z=0 且不共线')
    k, d = camera
    result = cv2.solvePnPGeneric(objects, pixels, k, d, flags=cv2.SOLVEPNP_IPPE)
    candidates = []
    for rv, tv in zip(result[1], result[2]):
        rv, tv = cv2.solvePnPRefineLM(objects, pixels, k, d, rv, tv)
        rotation = cv2.Rodrigues(rv)[0]
        center = -rotation.T @ tv.reshape(3)
        if center[2] <= max(s.get('height_m', 0) for s in tags.values()):
            continue
        if np.min((rotation @ objects.T + tv).T[:, 2]) <= 0:
            continue
        projected = cv2.projectPoints(objects, rv, tv, k, d)[0].reshape(-1, 2)
        error = float(np.sqrt(np.mean(np.sum((projected - pixels) ** 2, axis=1))))
        if math.isfinite(error):
            candidates.append((error, rotation, tv.reshape(3), center))
    if not candidates:
        raise ValueError('无法得到相机位于场地上方的外参；检查坐标、内参与标签')
    error, rotation, translation, center = min(candidates, key=lambda item: item[0])
    if error > 3:
        raise ValueError(f'四角重投影 RMS {error:.2f}px 超过 3px；检查测量/相机参数')
    return (rotation, translation), {'rms_px': error, 'camera_world_xyz_m': center.tolist(),
                                    'fixed_ids': [i for i, _ in specs]}


class DemoSource:
    """Oblique pinhole scene; no detection results are fabricated."""
    def __init__(self, settings):
        self.width, self.height = 1440, 1000
        self.k = np.array([[1420., 0, 720.], [0, 1420., 500.], [0, 0, 1.]])
        origin = np.array([1.5, -2.3, 4.8])
        forward = np.array([1.5, 1.4, 0.]) - origin
        forward /= np.linalg.norm(forward)
        right = np.cross(forward, [0., 0., 1.])
        right /= np.linalg.norm(right)
        down = np.cross(forward, right)
        self.rotation = np.array([right, down, forward])
        self.translation = -self.rotation @ origin
        self.rvec = cv2.Rodrigues(self.rotation)[0]
        self.config = copy.deepcopy(settings)
        self.config['family'] = 'tag36h11'
        # Keep the synthetic fleet independent of later changes to real hardware IDs.
        self.config['tags'] = {
            str(i): {'name': name, 'role': role, 'size_m': size, 'height_m': height, 'heading_offset_deg': 0}
            for i, name, role, size, height in [
                (0, '场地原点', 'fixed', .15, 0), (1, '场地 X 角', 'fixed', .15, 0),
                (2, '场地对角', 'fixed', .15, 0), (3, '场地 Y 角', 'fixed', .15, 0),
                (10, '追捕车 A', 'pursuer', .12, .12), (11, '追捕车 B', 'pursuer', .12, .12),
                (12, '追捕车 C', 'pursuer', .12, .12), (13, '逃逸车', 'evader', .12, .12)]}
        self.config['camera'] = {'image_width': self.width, 'image_height': self.height,
                                 'camera_matrix': self.k.tolist(), 'dist_coeffs': [0.] * 5}
        self.config['world'] = {'configured': True, 'boundary_xy_m': [[0, 0], [3, 0], [3, 3], [0, 3]]}
        self.patterns = {}
        for i in [0, 1, 2, 3, 10, 11, 12, 13]:
            name = ROOT / 'assets/apriltags' / f'tag36_11_{i:05d}.png'
            pattern = cv2.imread(str(name), cv2.IMREAD_GRAYSCALE)
            if pattern is None:
                raise ValueError('演示需要原有标签图案，请先运行 generate_apriltags.py')
            self.patterns[i] = cv2.resize(pattern, (300, 300), interpolation=cv2.INTER_NEAREST)
        self.started = time.monotonic()

    def project(self, xyz):
        return cv2.projectPoints(np.asarray(xyz, float), self.rvec, self.translation,
                                 self.k, None)[0].reshape(-1, 2)

    def read(self):
        frame = np.full((self.height, self.width, 3), (29, 36, 44), np.uint8)
        floor = self.project([[-.35, -.35, 0], [3.35, -.35, 0], [3.35, 3.35, 0], [-.35, 3.35, 0]])
        cv2.fillConvexPoly(frame, np.int32(floor), (203, 210, 211))
        for v in np.arange(0, 3.01, .5):
            for line in ([[v, 0, 0], [v, 3, 0]], [[0, v, 0], [3, v, 0]]):
                p = self.project(line).astype(int)
                cv2.line(frame, tuple(p[0]), tuple(p[1]), (180, 190, 191), 1, cv2.LINE_AA)
        t = time.monotonic() - self.started
        poses = {0: (0, 0, 0, 0), 1: (3, 0, 0, 0), 2: (3, 3, 0, 0), 3: (0, 3, 0, 0)}
        for j, i in enumerate([10, 11, 12]):
            a = t * .14 + j * math.pi * 2 / 3
            poses[i] = (1.5 + .85 * math.cos(a), 1.5 + .85 * math.sin(a), .12, a + math.pi / 2)
        poses[13] = (1.5 + .3 * math.cos(t * .23), 1.5 + .3 * math.sin(t * .18), .12, t * .23)
        for i, (x, y, z, angle) in poses.items():
            size = .15 if i < 4 else .12
            self.config['tags'][str(i)]['size_m'] = size
            self.config['tags'][str(i)]['height_m'] = z
            if i < 4:
                self.config['tags'][str(i)]['world_xyz_m'] = [x, y, z]
            # Includes the full 10-cell quiet zone around an 8-cell detection square.
            local = square_points(size * 1.25)[:, :2]
            rz = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
            xy = local @ rz.T + [x, y]
            dst = self.project(np.column_stack([xy, np.full(4, z)])).astype(np.float32)
            src = np.array([[0, 0], [299, 0], [299, 299], [0, 299]], np.float32)
            left, top = np.maximum(np.floor(dst.min(axis=0)).astype(int)-1, 0)
            right, bottom = np.minimum(np.ceil(dst.max(axis=0)).astype(int)+2, [self.width, self.height])
            if right <= left or bottom <= top:
                continue
            local_dst = dst - np.array([left, top], np.float32)
            warp = cv2.getPerspectiveTransform(src, local_dst)
            tile = cv2.warpPerspective(self.patterns[i], warp, (right-left, bottom-top),
                                       flags=cv2.INTER_NEAREST, borderValue=255)
            mask = np.zeros((bottom-top, right-left), np.uint8)
            cv2.fillConvexPoly(mask, np.int32(local_dst), 255)
            roi = frame[top:bottom, left:right]
            roi[mask > 0] = cv2.cvtColor(tile, cv2.COLOR_GRAY2BGR)[mask > 0]
        return True, frame

    def release(self):
        pass


class Tracker:
    def __init__(self):
        self.items = {}
        self.frames = 0
        self.started = time.monotonic()

    def update(self, detections, now, camera, extrinsic, specs):
        self.frames += 1
        visible = set()
        for raw in detections:
            ident = raw['id']
            if ident in visible:
                continue
            visible.add(ident)
            spec = specs.get(str(ident), {})
            old = self.items.get(ident)
            corners = np.asarray(raw['corners'])
            # Projective tag centre, not the mean of perspective-distorted corners.
            center = np.asarray(raw['center'])
            forward_px = (corners[0] + corners[1]) / 2
            heading = math.degrees(math.atan2(-(forward_px[1] - center[1]), forward_px[0] - center[0]))
            edges = np.linalg.norm(corners - np.roll(corners, -1, axis=0), axis=1)
            size = spec.get('size_m')
            pose = estimate_pose(corners, size, camera)
            # A calibrated tag-pose projection is preferable to a corner centroid.
            if pose is not None:
                k, d = camera
                projected = cv2.projectPoints(np.array([[0., 0., 0.], [0., size/2, 0.]]),
                                             np.array(pose['rvec_rad']), np.array(pose['camera_xyz_m']), k, d)[0].reshape(-1, 2)
                center, forward_px = projected
            known_height = spec.get('height_m')
            point = ray_to_plane(center, known_height, camera, extrinsic) if known_height is not None else None
            front = ray_to_plane(forward_px, known_height, camera, extrinsic) if known_height is not None else None
            world_heading = None
            if point is not None and front is not None:
                world_heading = (math.degrees(math.atan2(front[1]-point[1], front[0]-point[0]))
                                 + spec.get('heading_offset_deg', 0) + 180) % 360 - 180
            dt = now - old['last_monotonic'] if old else 0
            continuous = old is not None and 0 < dt <= .4
            speed_px = float(np.linalg.norm(center - old['center_px']) / dt) if continuous else None
            speed_m = None
            if continuous and point is not None and old['world_xyz_m'] is not None:
                speed_m = float(np.linalg.norm(point[:2] - np.array(old['world_xyz_m'][:2])) / dt)
            if continuous:
                for key, speed in [('speed_px_s', speed_px), ('speed_m_s', speed_m)]:
                    if speed is not None and old.get(key) is not None:
                        if key == 'speed_px_s':
                            speed_px = .3 * speed + .7 * old[key]
                        else:
                            speed_m = .3 * speed + .7 * old[key]
            history = old['history'] if old else deque(maxlen=100)
            history.append({'pixel': center.tolist(), 'world': point.tolist() if point is not None else None,
                            't': now - self.started})
            self.items[ident] = {'id': ident, 'name': spec.get('name', f'Tag {ident}'),
                'role': spec.get('role', 'unknown'), 'size_m': size, 'height_m': known_height,
                'center_px': center.tolist(), 'corners_px': corners.tolist(),
                'heading_image_deg': heading, 'heading_world_deg': world_heading,
                'min_edge_px': float(min(edges)), 'max_edge_px': float(max(edges)),
                'area_px2': float(abs(cv2.contourArea(corners.astype(np.float32)))),
                'decision_margin': raw['margin'], 'hamming': raw['hamming'], 'pose': pose,
                'world_xyz_m': point.tolist() if point is not None else None,
                'speed_px_s': speed_px, 'speed_m_s': speed_m,
                'seen_frames': (old['seen_frames'] if old else 0) + 1,
                'first_frame': old['first_frame'] if old else self.frames,
                'first_monotonic': old['first_monotonic'] if old else now,
                'last_monotonic': now, 'history': history}
        # Bound unknown-tag memory without removing the configured fleet.
        self.items = {i: t for i, t in self.items.items()
                      if str(i) in specs or now - t['last_monotonic'] < 30}
        return self.snapshot(now)

    def snapshot(self, now):
        out = []
        for ident, tag in sorted(self.items.items()):
            item = {k: v for k, v in tag.items() if k not in ('history', 'last_monotonic', 'first_monotonic', 'first_frame')}
            age = max(0, now - tag['last_monotonic'])
            item.update({'age_ms': age * 1000, 'status': 'visible' if age < .08 else 'stale' if age < .5 else 'lost',
                         'seen_ratio': tag['seen_frames'] / max(1, self.frames - tag['first_frame'] + 1),
                         'track_seconds': now - tag['first_monotonic'], 'history': list(tag['history'])})
            out.append(item)
        return out


class LiveEngine:
    def __init__(self, settings, source='demo', backend='auto', family='tag36h11', width=1280, height=720,
                 fps=30, runtime_path=None):
        self.settings = settings
        self.backend = backend
        self.width, self.height = width, height
        self.fps = fps
        self.runtime_path = runtime_path
        self.saved_world = None
        self.camera_id = str(source) if str(source).isdecimal() else '0'
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.pending = deque()
        self.source_name = str(source)
        self.family = family
        self.decimate = 1.0
        self.detector = Detector(family, self.decimate, backend)
        self.capture = None
        self.active = copy.deepcopy(settings)
        self.camera = None
        self.extrinsic = None
        self.world_info = None
        self.world_bad_frames = 0
        self.raw_detections = []
        self.latest_acquired = None
        self.tracker = Tracker()
        self.state = {'status': 'starting', 'tags': [], 'events': [], 'frame_id': 0}
        self.jpeg = None
        self.frame_id = 0
        self.running = True
        self.events = deque(maxlen=50)
        self.record = None
        self.thread = None

    def event(self, text, level='info'):
        self.events.appendleft({'time': datetime.now().strftime('%H:%M:%S'), 'text': text, 'level': level})

    def open_source(self, source):
        if source == 'disconnected':
            capture, active = None, copy.deepcopy(self.settings)
        elif source == 'demo':
            if self.family != 'tag36h11':
                raise ValueError('现有演示图案为 tag36h11，请选相同标签族')
            capture = DemoSource(self.settings)
            # Populate physical dimensions before exposing the config.
            capture.read()
            active = capture.config
        else:
            if source.isdecimal():
                value = int(source)
            else:
                path = Path(source).expanduser()
                if not path.is_file():
                    raise ValueError('视频文件不存在；摄像头请填数字索引，例如 0')
                value = str(path)
            capture = cv2.VideoCapture(value)
            if not capture.isOpened():
                capture.release()
                raise ValueError('无法打开相机/视频；检查相机索引、占用与系统相机权限')
            if isinstance(value, int):
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                capture.set(cv2.CAP_PROP_FPS, self.fps)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                # Verify a real frame before announcing a successful connection.
                frame = None
                for _ in range(10):
                    ok, frame = capture.read()
                    if ok and frame is not None:
                        break
                    time.sleep(.05)
                if frame is None:
                    capture.release()
                    raise ValueError('相机已打开但没有图像；请检查权限、占用或采集模式')
            active = copy.deepcopy(self.settings)
        if self.capture is not None:
            self.capture.release()
        self.capture, self.active = capture, active
        self.source_name = source
        if source.isdecimal():
            self.camera_id = source
        self.extrinsic, self.world_info, self.camera = None, None, None
        self.world_bad_frames = 0
        self.raw_detections = []
        self.latest_acquired = None
        self.tracker = Tracker()
        with self.condition:
            self.jpeg = None
            self.state = {'status': 'starting', 'tags': [], 'frame_id': self.frame_id,
                          'source': source, 'world_calibrated': False}
            self.condition.notify_all()
        self.event('已连接合成演示（真实检测器）' if source == 'demo' else f'已连接输入源 {source}')

    def configuration(self):
        with self.lock:
            return copy.deepcopy({
                'source': self.camera_id, 'enabled': self.source_name.isdecimal() and self.capture is not None,
                'width': self.width, 'height': self.height, 'fps': self.fps,
                'family': self.family, 'decimate': self.decimate,
                'camera': self.settings.get('camera'), 'tags': self.settings['tags'],
                'world': self.settings.get('world', {'configured': False}),
                'saved_world': self.saved_world is not None,
            })

    def persist_configuration(self):
        save_runtime(self.runtime_path, {'profile': self.configuration(), 'saved_world': self.saved_world})

    def configure(self, profile):
        profile = validate_profile(profile)
        detector = Detector(profile['family'], profile['decimate'], self.backend)
        old = (self.settings, self.width, self.height, self.fps, self.family, self.decimate, self.detector)
        old_profile, old_world, old_source = self.configuration(), self.saved_world, self.source_name
        self.settings = {key: copy.deepcopy(profile[key]) for key in ('camera', 'tags', 'world', 'family')}
        self.width, self.height, self.fps = profile['width'], profile['height'], profile['fps']
        self.family, self.decimate, self.detector = profile['family'], profile['decimate'], detector
        try:
            # Drivers commonly reject opening an already occupied camera. Release it first.
            if self.capture is not None and self.source_name == profile['source']:
                self.capture.release()
                self.capture = None
            self.open_source(profile['source'] if profile['enabled'] else 'disconnected')
            self.camera_id = profile['source']
            # Disconnect/reconnect of an identical profile retains a manually loadable calibration.
            comparable = lambda p: {k: v for k, v in p.items() if k not in ('enabled', 'saved_world')}
            if comparable(old_profile) != comparable(profile):
                self.saved_world = None
            self.persist_configuration()
        except (ValueError, RuntimeError, OSError, cv2.error):
            (self.settings, self.width, self.height, self.fps, self.family, self.decimate, self.detector) = old
            self.saved_world, self.camera_id = old_world, old_profile['source']
            try:
                self.open_source(old_source)
            except (ValueError, OSError, cv2.error):
                self.open_source('disconnected')
            raise
        self.event('相机与物理配置已保存；请确认内参后重新锁定场地外参')

    def execute(self, payload, timeout=20):
        """Wait for the capture worker's result, including actual driver/calibration failures."""
        completion = {'event': threading.Event(), 'started': False, 'cancelled': False}
        self.command(payload, completion)
        if not completion['event'].wait(timeout):
            with self.lock:
                completion['cancelled'] = not completion['started']
            raise TimeoutError('相机操作超时；请检查设备并刷新状态，全车应保持锁定')
        if 'error' in completion:
            raise ValueError(completion['error'])
        return completion.get('result', self.configuration())

    def command(self, payload, completion=None):
        if not isinstance(payload, dict):
            raise ValueError('Expected a JSON object')
        action = payload.get('action')
        if action not in ('source', 'detector', 'calibrate', 'reset_world', 'clear_tracks', 'record',
                          'configure', 'scan_cameras', 'load_world'):
            raise ValueError('Unknown action')
        if action == 'source':
            source = payload.get('source', '')
            if not isinstance(source, str) or not source.strip() or len(source) > 1024:
                raise ValueError('Invalid source')
            payload = {'action': action, 'source': source.strip()}
        if action == 'detector':
            family = payload.get('family', self.family)
            if family not in self.detector.families:
                raise ValueError('Unsupported family for this backend')
            decimate = finite_number(payload.get('decimate', 1), 'decimate', 1, 4)
            payload = {'action': action, 'family': family, 'decimate': decimate}
        if action == 'configure':
            payload = {'action': action, 'profile': validate_profile(payload.get('profile'))}
        payload = dict(payload)
        if completion is not None:
            payload['_completion'] = completion
        with self.lock:
            if len(self.pending) > 8:
                raise ValueError('请等待上一个操作完成')
            self.pending.append(payload)

    def tag_specs(self):
        return self.active['tags'] if self.family == self.active.get('family', 'tag36h11') else {}

    def apply_commands(self):
        with self.lock:
            commands = list(self.pending)
            self.pending.clear()
        for p in commands:
            completion = p.get('_completion')
            if completion is not None:
                with self.lock:
                    if completion['cancelled']:
                        completion['event'].set()
                        continue
                    completion['started'] = True
            try:
                action = p['action']
                if action in ('source', 'detector', 'calibrate', 'reset_world', 'configure', 'load_world') and self.record:
                    self.stop_recording()
                if action == 'configure':
                    self.configure(p['profile'])
                elif action == 'scan_cameras':
                    devices = discover_cameras(self.source_name, self.capture)
                    if completion is not None:
                        completion['result'] = {'cameras': devices, 'scanned_indices': [0, 5]}
                elif action == 'source':
                    self.open_source(p['source'])
                elif action == 'detector':
                    if self.source_name == 'demo' and p['family'] != 'tag36h11':
                        raise ValueError('演示仅提供 tag36h11 图案；接入实物相机后可切换其他族')
                    detector = Detector(p['family'], p['decimate'], self.backend)
                    self.detector = detector
                    self.family, self.decimate = p['family'], p['decimate']
                    self.tracker = Tracker()
                    self.raw_detections = []
                    self.extrinsic, self.world_info = None, None
                    self.event(f'检测器：{self.family}，降采样 {self.decimate:g}×')
                elif action == 'calibrate':
                    if self.latest_acquired is None or time.monotonic() - self.latest_acquired > .3:
                        raise ValueError('当前图像已过期；请恢复输入源后再锁定外参')
                    if not self.tag_specs():
                        raise ValueError('标签族与物理尺寸配置不匹配，请更新 apriltag_live.json')
                    if not self.active.get('world', {}).get('configured'):
                        raise ValueError('先在 apriltag_live.json 中填实测坐标并将 world.configured 设为 true')
                    self.extrinsic, self.world_info = calibrate_world(
                        self.raw_detections, self.tag_specs(), self.camera)
                    self.world_bad_frames = 0
                    self.tracker = Tracker()
                    self.saved_world = {'rotation': self.extrinsic[0].tolist(),
                                        'translation': self.extrinsic[1].tolist(), 'info': self.world_info,
                                        'profile': self.configuration()}
                    self.persist_configuration()
                    self.event(f'场地外参已锁定，RMS {self.world_info["rms_px"]:.2f}px；移动相机后需重标')
                elif action == 'load_world':
                    saved = self.saved_world
                    if saved is None or self.camera is None or self.latest_acquired is None or time.monotonic() - self.latest_acquired > .3:
                        raise ValueError('没有可加载的标定，或相机尚无有效的新鲜图像')
                    current = self.configuration()
                    if any(saved['profile'].get(k) != current.get(k) for k in
                           ('source', 'width', 'height', 'camera', 'tags', 'world', 'family')):
                        raise ValueError('已保存标定与当前相机或物理配置不一致，请重新标定')
                    # Re-solve from currently visible fixed tags; never trust stale camera placement.
                    extrinsic, info = calibrate_world(self.raw_detections, self.tag_specs(), self.camera)
                    if np.linalg.norm(np.array(saved['info']['camera_world_xyz_m']) - info['camera_world_xyz_m']) > .03:
                        raise ValueError('相机位置与保存标定不一致，请重新标定')
                    self.extrinsic, self.world_info = extrinsic, info
                    self.tracker = Tracker()
                    self.event('已核验并加载场地标定')
                elif action == 'reset_world':
                    self.extrinsic, self.world_info = None, None
                    self.tracker = Tracker()
                    self.saved_world = None
                    self.persist_configuration()
                    self.event('已清除场地标定')
                elif action == 'clear_tracks':
                    self.tracker = Tracker()
                    self.event('已清除轨迹和累计统计')
                elif action == 'record':
                    if self.record:
                        self.stop_recording()
                    else:
                        folder = ROOT / 'output/live' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                        folder.mkdir(parents=True)
                        (folder / 'config.json').write_text(json.dumps(
                            {'source': self.source_name, 'demo': self.source_name == 'demo',
                             'family': self.family, 'settings': self.active, 'world_info': self.world_info,
                             'extrinsic_world_to_camera': None if self.extrinsic is None else
                             {'rotation': self.extrinsic[0].tolist(), 'translation_m': self.extrinsic[1].tolist()}},
                            ensure_ascii=False, indent=2), encoding='utf-8')
                        self.record = {'folder': folder, 'stream': (folder/'frames.jsonl').open('w', encoding='utf-8'), 'frames': 0}
                        self.event(f'开始记录：{folder.relative_to(ROOT)}')
            except (ValueError, RuntimeError, cv2.error, OSError) as error:
                self.event(str(error), 'error')
                if completion is not None:
                    completion['error'] = str(error)
            finally:
                if completion is not None:
                    completion['event'].set()

    def stop_recording(self):
        if self.record:
            record = self.record
            self.record = None
            record['stream'].close()
            self.event(f'已保存 {record["frames"]} 帧：{record["folder"].relative_to(ROOT)}')

    def overlay(self, frame, tags):
        for t in tags:
            if t['age_ms'] > 80:
                continue
            color = COLORS[t['id'] % len(COLORS)]
            points = np.int32(t['corners_px'])
            cv2.polylines(frame, [points], True, color, 2, cv2.LINE_AA)
            c = tuple(np.int32(t['center_px']))
            front = tuple(np.int32((points[0] + points[1]) / 2))
            cv2.arrowedLine(frame, c, front, color, 2, cv2.LINE_AA, tipLength=.3)
            cv2.drawMarker(frame, c, color, cv2.MARKER_CROSS, 12, 1)
            for j, point in enumerate(points):
                cv2.circle(frame, tuple(point), 3, (255, 255, 255), -1)
                cv2.putText(frame, str(j), tuple(point + [4, -4]), cv2.FONT_HERSHEY_SIMPLEX, .32, color, 1, cv2.LINE_AA)
            text = f'ID {t["id"]} | {t["min_edge_px"]:.0f}px'
            if t['pose']:
                text += f' | {t["pose"]["range_m"]:.2f}m'
                if self.camera:
                    cv2.drawFrameAxes(frame, *self.camera, np.array(t['pose']['rvec_rad']),
                                      np.array(t['pose']['camera_xyz_m']), t['size_m'] * .65, 2)
            loc = (max(0, int(points[:, 0].min())), max(20, int(points[:, 1].min()) - 10))
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, .47, 1)
            cv2.rectangle(frame, (loc[0]-3, loc[1]-th-6), (loc[0]+tw+4, loc[1]+4), (16, 25, 32), -1)
            cv2.putText(frame, text, loc, cv2.FONT_HERSHEY_SIMPLEX, .47, color, 1, cv2.LINE_AA)
            history = [h['pixel'] for h in t['history']]
            if len(history) > 1 and t['role'] != 'fixed':
                cv2.polylines(frame, [np.int32(history)], False, color, 1, cv2.LINE_AA)
        label = 'SYNTHETIC DEMO - REAL DETECTOR' if self.source_name == 'demo' else f'LIVE / {self.family}'
        cv2.rectangle(frame, (14, 14), (440, 47), (18, 28, 36), -1)
        cv2.putText(frame, label, (24, 36), cv2.FONT_HERSHEY_SIMPLEX, .52, (100, 224, 189), 1, cv2.LINE_AA)
        return frame

    def run(self):
        try:
            self.open_source(self.source_name)
        except (ValueError, OSError, cv2.error) as error:
            self.event(str(error), 'error')
        previous, fps = time.monotonic(), 0.
        last_state = None
        while self.running:
            began = time.monotonic()
            self.apply_commands()
            try:
                if self.capture is None:
                    raise ValueError('相机未连接，请选择相机并连接')
                ok, frame = self.capture.read()
                acquired = time.monotonic()
                if not ok or frame is None:
                    raise ValueError('输入源没有新帧（相机断开或视频结束）；请重新连接')
                self.latest_acquired = acquired
                h, w = frame.shape[:2]
                calibration_error = None
                try:
                    self.camera = camera_at_size(self.active['camera'], w, h)
                except ValueError as error:
                    self.camera = None
                    self.extrinsic, self.world_info = None, None
                    calibration_error = str(error)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                start = time.perf_counter()
                detections = self.detector.detect(gray)
                detection_ms = (time.perf_counter() - start) * 1000
                self.raw_detections = detections
                # Detector normally suppresses duplicates; reject any residual ambiguous identity.
                ids = [t['id'] for t in detections]
                duplicates = {i for i in ids if ids.count(i) > 1}
                detections = [t for t in detections if t['id'] not in duplicates]
                self.raw_detections = detections
                if self.extrinsic is not None and self.camera is not None:
                    fixed = [(t, self.tag_specs().get(str(t['id']), {})) for t in detections]
                    fixed = [(t, spec) for t, spec in fixed if spec.get('role') == 'fixed' and spec.get('world_xyz_m') is not None]
                    residual = None
                    if len(fixed) >= 2:
                        rotation, translation = self.extrinsic
                        points = np.array([spec['world_xyz_m'] for _, spec in fixed], float)
                        predicted = cv2.projectPoints(points, cv2.Rodrigues(rotation)[0], translation, *self.camera)[0].reshape(-1, 2)
                        observed = np.array([t['center'] for t, _ in fixed])
                        residual = float(np.sqrt(np.mean(np.sum((predicted-observed)**2, axis=1))))
                    self.world_info['monitor_rms_px'] = residual
                    self.world_bad_frames = self.world_bad_frames+1 if residual is not None and residual > 5 else 0
                    if self.world_bad_frames >= 3:
                        self.extrinsic, self.world_info = None, None
                        self.tracker = Tracker()
                        self.world_bad_frames = 0
                        self.event('固定标签重投影偏差持续 >5px，已清除场地外参；检查相机/标签是否移动后重标', 'error')
                tags = self.tracker.update(detections, acquired, self.camera, self.extrinsic, self.tag_specs())
                current_ids = {t['id'] for t in detections}
                for t in tags:
                    t['status'] = 'visible' if t['id'] in current_ids else ('stale' if t['age_ms'] < 500 else 'lost')
                now = time.monotonic()
                interval = now - previous
                fps = (1 / interval) if fps == 0 else .15 / interval + .85 * fps
                previous = now
                thumbnail = cv2.resize(gray, (320, 220))
                warnings = []
                if self.camera is None:
                    warnings.append(calibration_error or '相机未标定：距离、三维位姿、米制位置与速度不可用')
                elif self.extrinsic is None:
                    warnings.append('尚未锁定四角外参：场地坐标与米制速度不可用')
                if self.source_name == 'demo':
                    warnings.append('合成演示：虚拟内参和尺寸，仅用于功能验证，不代表实机精度')
                elif not self.source_name.isdecimal():
                    warnings.append('视频回放：速度按主机处理时钟估计，不代表原始录像的真实速度')
                if duplicates:
                    warnings.append(f'重复 ID 已剔除：{sorted(duplicates)}；每个实体请使用不同 ID')
                if not self.tag_specs():
                    warnings.append('检测标签族与物理配置不匹配：只显示像素信息，请更新配置后重启')
                if any(t['min_edge_px'] < 35 for t in tags if t['status'] == 'visible'):
                    warnings.append('部分标签短边 <35px；识别距离/斜视压缩需现场验证')
                if any(t['decision_margin'] is not None and t['decision_margin'] < 30 for t in tags if t['status'] == 'visible'):
                    warnings.append('部分解码裕量偏低；该值不是识别置信概率')
                state = {'status': 'running', 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                    'frame_id': self.frame_id + 1, 'source': self.source_name, 'demo': self.source_name == 'demo',
                    'source_kind': ('demo' if self.source_name == 'demo' else
                                    'camera' if self.source_name.isdecimal() else 'file'),
                    'family': self.family, 'backend': self.detector.name, 'families': self.detector.families,
                    'decimate': self.decimate, 'width': w, 'height': h, 'fps': fps,
                    'detection_ms': detection_ms, 'processing_ms': (now - acquired)*1000,
                    'mean_brightness': float(np.mean(thumbnail)),
                    'laplacian_variance': float(cv2.Laplacian(thumbnail, cv2.CV_64F).var()),
                    'visible_count': len(current_ids), 'known_count': len(self.tag_specs()),
                    'calibrated': self.camera is not None, 'world_calibrated': self.extrinsic is not None,
                    'world_info': self.world_info, 'boundary_xy_m': self.active.get('world', {}).get('boundary_xy_m'),
                    'tags': tags, 'configured_tags': self.tag_specs(), 'warnings': warnings,
                    'acquired_monotonic': acquired, 'tag_age_reference_monotonic': acquired}
                annotated = self.overlay(frame, tags)
                success, encoded = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not success:
                    raise ValueError('JPEG编码失败')
                state['processing_ms'] = (time.monotonic() - acquired) * 1000
                with self.condition:
                    self.frame_id += 1
                    self.jpeg = encoded.tobytes()
                    state['events'] = list(self.events)
                    state['recording'] = self.record is not None
                    state['record_path'] = str(self.record['folder'].relative_to(ROOT)) if self.record else None
                    state['updated_monotonic'] = time.monotonic()
                    self.state = state
                    last_state = state
                    self.condition.notify_all()
                if self.record:
                    # Include empty frames and stale tags so missing data stays observable.
                    row = {k: v for k, v in state.items() if k not in ('events', 'updated_monotonic', 'acquired_monotonic', 'tag_age_reference_monotonic', 'configured_tags')}
                    row['tags'] = [{k: v for k, v in t.items() if k != 'history'} for t in tags]
                    self.record['stream'].write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
                    self.record['stream'].flush()
                    self.record['frames'] += 1
            except (ValueError, RuntimeError, OSError, cv2.error) as error:
                message = str(error)
                with self.condition:
                    if self.state.get('error') != message:
                        self.event(message, 'error')
                    state = copy.deepcopy(last_state) if last_state else {'tags': [], 'frame_id': self.frame_id}
                    state.update({'status': 'error', 'error': message, 'visible_count': 0,
                                  'fps': 0, 'events': list(self.events), 'recording': self.record is not None,
                                  'updated_monotonic': time.monotonic(), 'tag_age_reference_monotonic': time.monotonic()})
                    for t in state['tags']:
                        t['status'] = 'lost'
                        tracked = self.tracker.items.get(t['id'])
                        t['age_ms'] = (time.monotonic()-tracked['last_monotonic'])*1000 if tracked else None
                    self.state = state
                    self.condition.notify_all()
                if self.record:
                    self.stop_recording()
                time.sleep(.2)
            # A bounded rate prevents a video file/demo from consuming a whole CPU core.
            time.sleep(max(0, 1/25 - (time.monotonic() - began)))
        self.stop_recording()
        if self.capture is not None:
            self.capture.release()

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True, name='apriltag-capture')
        self.thread.start()

    def stop(self):
        self.running = False
        with self.condition:
            self.condition.notify_all()
        if self.thread:
            self.thread.join(timeout=3)

    def snapshot(self):
        with self.lock:
            state = copy.deepcopy(self.state)
        updated = state.pop('updated_monotonic', None)
        acquired = state.pop('acquired_monotonic', None)
        tag_age_reference = state.pop('tag_age_reference_monotonic', None)
        if tag_age_reference:
            delta = max(0, time.monotonic() - tag_age_reference) * 1000
            for tag in state.get('tags', []):
                if tag.get('age_ms') is not None:
                    tag['age_ms'] += delta
                    if tag['age_ms'] > 500:
                        tag['status'] = 'lost'
                    elif tag['age_ms'] > 200:
                        tag['status'] = 'stale'
        if 'visible_count' in state:
            state['visible_count'] = sum(t.get('status') == 'visible' for t in state.get('tags', []))
        state['state_age_ms'] = (time.monotonic() - updated) * 1000 if updated else None
        state['frame_age_ms'] = (time.monotonic() - acquired) * 1000 if acquired else None
        return state


def create_app(engine):
    app = Flask(__name__, static_folder=str(ROOT/'web'), static_url_path='/assets')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024

    @app.before_request
    def local_mutations_only():
        # No cross-origin page may operate the host's camera or recording.
        if request.method == 'POST':
            origin = request.headers.get('Origin')
            if origin and origin != request.host_url.rstrip('/'):
                return jsonify(error='Cross-origin requests are not allowed'), 403
            if not request.is_json:
                return jsonify(error='Use application/json'), 415

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/')
    def index():
        return send_file(ROOT/'web/index.html')

    @app.get('/api/state')
    def state():
        return jsonify(engine.snapshot())

    @app.get('/api/config')
    def configuration():
        return jsonify(config=engine.configuration(), state=engine.snapshot())

    def execute_camera(payload):
        try:
            result = engine.execute(payload)
            return jsonify(result)
        except (ValueError, TypeError) as error:
            return jsonify(error=str(error)), 400
        except TimeoutError as error:
            return jsonify(error=str(error)), 504

    @app.post('/api/config')
    def configure():
        return execute_camera({'action': 'configure', 'profile': request.get_json(silent=True)})

    @app.post('/api/cameras')
    def cameras():
        return execute_camera({'action': 'scan_cameras'})

    @app.post('/api/operations')
    def operation():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or payload.get('action') not in ('calibrate', 'reset_world', 'load_world'):
            return jsonify(error='不支持的标定操作'), 400
        return execute_camera(payload)

    @app.post('/api/control')
    def control():
        try:
            engine.command(request.get_json(silent=True))
        except (ValueError, TypeError) as error:
            return jsonify(error=str(error)), 400
        return jsonify(queued=True), 202

    @app.get('/stream.mjpg')
    def stream():
        def frames():
            last = -1
            while engine.running:
                with engine.condition:
                    engine.condition.wait_for(lambda: engine.frame_id != last or not engine.running, timeout=1)
                    if not engine.running:
                        break
                    frame_id, data = engine.frame_id, engine.jpeg
                if data is None or frame_id == last:
                    continue
                last = frame_id
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + data + b'\r\n'
        return Response(frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.get('/api/snapshot.jpg')
    def snapshot():
        with engine.lock:
            data = engine.jpeg
        if data is None:
            return jsonify(error='No frame yet'), 503
        return send_file(io.BytesIO(data), mimetype='image/jpeg', as_attachment=True,
                         download_name=f'apriltag_{datetime.now():%Y%m%d_%H%M%S}.jpg')

    @app.get('/api/export.json')
    def export():
        data = json.dumps(engine.snapshot(), ensure_ascii=False, indent=2, allow_nan=False).encode()
        return send_file(io.BytesIO(data), mimetype='application/json', as_attachment=True, download_name='apriltag_state.json')

    @app.get('/api/export.csv')
    def export_csv():
        output = io.StringIO(newline='')
        keys = ['id', 'name', 'role', 'status', 'age_ms', 'center_x_px', 'center_y_px',
                'heading_image_deg', 'world_x_m', 'world_y_m', 'height_m', 'heading_world_deg',
                'speed_px_s', 'speed_m_s', 'decision_margin', 'hamming', 'min_edge_px',
                'camera_x_m', 'camera_y_m', 'camera_z_m', 'range_m', 'reprojection_rms_px', 'seen_ratio']
        writer = csv.DictWriter(output, fieldnames=keys)
        writer.writeheader()
        for tag in engine.snapshot()['tags']:
            row = {k: tag.get(k) for k in keys}
            row['center_x_px'], row['center_y_px'] = tag['center_px']
            if tag['world_xyz_m']:
                row['world_x_m'], row['world_y_m'] = tag['world_xyz_m'][:2]
            pose = tag['pose']
            if pose:
                row['camera_x_m'], row['camera_y_m'], row['camera_z_m'] = pose['camera_xyz_m']
                row['range_m'], row['reprojection_rms_px'] = pose['range_m'], pose['reprojection_rms_px']
            writer.writerow(row)
        return send_file(io.BytesIO(('\ufeff' + output.getvalue()).encode()), mimetype='text/csv',
                         as_attachment=True, download_name='apriltag_current_tags.csv')

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default=None, help='demo, camera index (0), or a video file; defaults to saved profile or demo')
    parser.add_argument('--config', type=Path, default=ROOT/'apriltag_live.json')
    parser.add_argument('--family', default='tag36h11', choices=NATIVE_FAMILIES)
    parser.add_argument('--backend', choices=['auto', 'native', 'opencv'], default='auto')
    parser.add_argument('--width', type=int)
    parser.add_argument('--height', type=int)
    parser.add_argument('--fps', type=float)
    parser.add_argument('--runtime-config', type=Path, default=ROOT/'output/vision-settings.json')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    settings = load_settings(args.config)
    profile, saved_world = {}, None
    if args.runtime_config.is_file():
        runtime = json.loads(args.runtime_config.read_text(encoding='utf-8'))
        profile = validate_profile(runtime['profile'])
        saved_world = runtime.get('saved_world')
        settings = {key: profile[key] for key in ('camera', 'tags', 'world', 'family')}
    source = args.source if args.source is not None else (
        profile['source'] if profile.get('enabled') else 'disconnected' if profile else 'demo')
    engine = LiveEngine(settings, source, args.backend, args.family,
                        args.width or profile.get('width', 1280), args.height or profile.get('height', 720),
                        args.fps or profile.get('fps', 30), args.runtime_config)
    engine.camera_id = profile.get('source', engine.camera_id)
    engine.decimate = profile.get('decimate', 1)
    engine.detector = Detector(engine.family, engine.decimate, engine.backend)
    engine.saved_world = saved_world
    engine.start()
    print(f'AprilTag dashboard: http://127.0.0.1:{args.port} (source={source})', flush=True)
    try:
        create_app(engine).run(host='127.0.0.1', port=args.port, threaded=True, debug=False, use_reloader=False)
    finally:
        engine.stop()


if __name__ == '__main__':
    main()
