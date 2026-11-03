"""Consume only fresh, calibrated live-camera poses; reject malformed frames."""
import asyncio
import logging
import math
import time
from collections import Counter

import httpx

log = logging.getLogger(__name__)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def reject(fleet, r, reason):
    if r.armed or (r.pending and r.pending["action"] == "arm"):
        fleet.stop(r, reason)
    r.pose_at = 0


def ingest(fleet, data, began, last_frame):
    if not isinstance(data, dict):
        raise ValueError("视觉响应必须是对象")
    frame_id, timestamp = data.get("frame_id"), data.get("timestamp_utc")
    frame = (timestamp, frame_id)
    age, fps = data.get("frame_age_ms"), data.get("fps", 0)
    source = data.get("source_kind")
    valid = (data.get("status") == "running" and data.get("demo") is False
             and source == "camera" and data.get("world_calibrated") is True
             and data.get("family") == "tag36h11"
             and type(frame_id) is int and frame_id >= 0
             and isinstance(timestamp, str) and bool(timestamp)
             and number(age) and 0 <= age < 200)
    fresh = valid and frame != last_frame
    available = (data.get('status') == 'running' and data.get('demo') is False and source == 'camera'
                 and number(age) and 0 <= age < 1000)
    fleet.camera = {"connected": fresh, "available": available,
                    "fps": fps if number(fps) and fps >= 0 else 0,
                    "reason": "视觉已连接" if fresh else "相机已连接，请完成场地标定" if available
                    else data.get('error', "等待新鲜、已标定的实时相机数据")}
    if not valid:
        # A source switch or invalid calibration invalidates old poses immediately.
        for r in fleet.robots.values():
            r.pose_at = 0
        return last_frame
    if not fresh:
        return last_frame
    tags = data.get("tags")
    if not isinstance(tags, list):
        raise ValueError("tags必须是列表")
    ids = Counter(t.get("id") for t in tags if isinstance(t, dict) and type(t.get("id")) is int)
    by_id = {t["id"]: t for t in tags if isinstance(t, dict) and type(t.get("id")) is int
             and ids[t["id"]] == 1}
    now = time.monotonic()
    for r in fleet.robots.values():
        tag = by_id.get(r.config.tag_id)
        if not tag or tag.get("status") != "visible":
            continue
        xyz, degrees, tag_age = tag.get("world_xyz_m"), tag.get("heading_world_deg"), tag.get("age_ms")
        if (not isinstance(xyz, list) or len(xyz) != 3 or
                not all(number(v) for v in [*xyz, degrees, tag_age]) or tag_age < 0):
            continue
        quality = [(tag.get("min_edge_px"), 35, float("inf")),
                   (tag.get("decision_margin"), 30, float("inf")), (tag.get("hamming"), 0, 0)]
        if any(value is not None and (not number(value) or not low <= value <= high)
               for value, low, high in quality):
            reject(fleet, r, "定位质量不足 · 已锁定")
            continue
        source_age = max(age, tag_age) / 1000 + now - began
        if not 0 <= source_age < .2:
            continue
        theta = math.radians(degrees) + r.config.heading_offset
        theta = math.atan2(math.sin(theta), math.cos(theta))
        c, s = math.cos(theta), math.sin(theta)
        x = xyz[0] - c*r.config.tag_offset_x + s*r.config.tag_offset_y
        y = xyz[1] - s*r.config.tag_offset_x - c*r.config.tag_offset_y
        at = now-source_age
        if r.pose_at:
            dt = at-r.pose_at
            if dt <= 0:
                continue
            max_v, max_omega = fleet.limits(r)
            turn = math.atan2(math.sin(theta-r.theta), math.cos(theta-r.theta))
            if dt <= .2 and (math.hypot(x-r.x, y-r.y) > .04+3*max_v*dt or
                             abs(turn) > .35+3*max_omega*dt):
                reject(fleet, r, "定位跳变 · 已锁定")
                continue
        fleet.pose(r, x, y, theta, at)
    return frame


async def watch(fleet, base_url):
    last_frame = None
    async with httpx.AsyncClient(timeout=.7) as client:
        while True:
            began = time.monotonic()
            url = base_url() if callable(base_url) else base_url
            revision = (fleet.session, fleet.vision_revision)
            if not url or fleet.vision_updating or fleet.vision_sync_error:
                await asyncio.sleep(.05)
                continue
            try:
                response = await client.get(url + "/api/state")
                response.raise_for_status()
                if fleet.vision_updating or fleet.vision_sync_error or revision != (fleet.session, fleet.vision_revision):
                    continue
                last_frame = ingest(fleet, response.json(), began, last_frame)
            except (httpx.HTTPError, ValueError, KeyError, TypeError, OverflowError) as exc:
                if revision != (fleet.session, fleet.vision_revision):
                    continue
                fleet.camera = {"connected": False, "fps": 0, "reason": "视觉数据无效或服务不可用"}
                log.debug("Vision unavailable: %s", exc)
            await asyncio.sleep(max(0, .05-(time.monotonic()-began)))
