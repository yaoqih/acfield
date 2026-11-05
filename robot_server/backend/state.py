"""Single event-loop owner for state, handshakes and motion interlocks."""
import math
import os
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from .models import Command, DeviceLimits, RobotConfig, Settings, Telemetry
from . import safety

POSE_TTL = .2
HEARTBEAT_TTL = 1.
RETRY_INTERVAL = .15
OWNER_TTL = 10.


@dataclass
class Robot:
    config: RobotConfig
    x: float | None = None
    y: float | None = None
    theta: float | None = None
    pose_at: float = 0
    seen_at: float = 0
    battery: float | None = None
    voltage_v: float | None = None
    measured_v: float | None = None
    measured_omega: float | None = None
    wheel_left: float | None = None
    wheel_right: float | None = None
    encoder_left: int | None = None
    encoder_right: int | None = None
    estimated_v: float | None = None
    acceleration: float | None = None
    armed: bool = False
    bound: bool = False
    device_state: str | None = None
    firmware: str | None = None
    stop_reason: str | None = None
    limits: DeviceLimits | None = None
    owner: str | None = None
    owner_until: float = 0
    target_v: float = 0
    target_omega: float = 0
    deadline: float = 0
    seq: int = 0
    ack_seq: int = -1
    command_status: str = "idle"
    pending: dict | None = None
    pending_at: float = 0
    retry_at: float = 0
    endpoint: tuple | None = None
    boot_id: str | None = None
    telemetry_seq: int = -1
    retired_boots: set = field(default_factory=set)
    fault: str | None = None
    reason: str = "等待解锁"
    trail: deque = field(default_factory=lambda: deque(maxlen=180))


class Fleet:
    def __init__(self, settings: Settings, mode: str):
        self.settings = settings
        self.mode = mode
        self.allow_unlocalized_control = os.getenv("ROBOT_ALLOW_UNLOCALIZED_CONTROL", "0") == "1"
        self.session = uuid.uuid4().hex
        self.robots = {c.id: Robot(c, bound=mode == "demo") for c in settings.robots}
        self.estop = False
        self.runtime_fault = None
        self.vision_updating = False
        self.vision_sync_error = None
        self.vision_revision = 0
        self.control_at = time.monotonic()
        self.send = lambda packet, endpoint: None
        self.record = lambda kind, data: None
        self.events = deque(maxlen=40)
        self.camera = {"connected": False, "reason": "未连接视觉服务", "fps": 0}
        self.event("系统启动 · " + ("四车模拟" if mode == "demo" else "真实设备"))

    def event(self, message):
        self.events.appendleft({"time": time.time(), "message": message})
        self.record("event", {"message": message})

    def robot(self, ident):
        return self.robots[ident]

    def ready(self, r, now):
        if self.vision_sync_error:
            return self.vision_sync_error
        if self.vision_updating:
            return "视觉配置正在更新，请等待操作完成"
        if self.runtime_fault:
            return "控制服务故障，请重启服务：" + self.runtime_fault
        if self.estop:
            return "全局停止已锁定"
        if r.fault:
            return "设备故障：" + r.fault
        if not r.seen_at or now-r.seen_at > HEARTBEAT_TTL:
            return "设备离线"
        if not r.bound:
            return "等待车端停车绑定确认，请确认固件已更新"
        if not self.allow_unlocalized_control and (not r.pose_at or now-r.pose_at > POSE_TTL):
            return "定位已过期"
        return None

    def arm(self, r, enabled, owner="local"):
        if not enabled:
            self.stop(r, "已锁定")
            return
        now = time.monotonic()
        reason = self.ready(r, now)
        if reason:
            raise ValueError(reason)
        if r.owner and r.owner != owner:
            raise ValueError("另一控制页面已取得控制权，请先锁定小车")
        if r.armed or (r.pending and r.pending["action"] == "arm"):
            return
        r.owner, r.owner_until = owner, now+OWNER_TTL
        if self.mode == "demo":
            r.armed, r.device_state = True, "armed"
            r.reason = "已解锁 · 等待指令"
        else:
            self.request(r, "arm", now)
            r.reason = "等待车端解锁确认"
        self.event(f"{r.config.name} · 请求解锁")

    def release(self, r, owner):
        """Check and release in one event-loop operation; never stop a new owner."""
        if r.owner != owner:
            return False
        self.stop(r, "控制源已释放 · 已锁定")
        return True

    def packet(self, r, v, omega, ttl_ms, action="drive"):
        r.seq += 1
        packet = {"version": 1, "type": "command", "session": self.session,
                  "robot_id": r.config.id, "boot_id": r.boot_id, "telemetry_seq": r.telemetry_seq,
                  "seq": r.seq, "v": v, "omega": omega, "action": action,
                  "ttl_ms": ttl_ms, "stop": v == 0 and omega == 0}
        self.record("command", packet.copy())
        if self.mode == "demo":
            r.ack_seq, r.command_status = r.seq, "confirmed"
        elif r.endpoint and r.telemetry_seq >= 0:
            self.send(packet, r.endpoint)
            r.command_status = "sent"
        return packet

    def request(self, r, action, now):
        if self.mode == "hardware" and r.endpoint and r.telemetry_seq >= 0:
            r.pending = self.packet(r, 0, 0, 100, action)
            r.pending_at, r.retry_at = now, now+RETRY_INTERVAL
            return r.pending

    def command(self, r, cmd: Command, owner="local"):
        return self.commands({r.config.id: cmd}, owner)[r.config.id]

    def commands(self, commands: dict[str, Command], owner="local"):
        """Validate a shared set of candidate velocities before sending any of them."""
        now = time.monotonic()
        robots = {ident: self.robot(ident) for ident in sorted(commands)}
        targets = {}
        request = {ident: cmd.model_dump() for ident, cmd in commands.items()}
        try:
            for ident, r in robots.items():
                cmd = commands[ident]
                if cmd.v or cmd.omega:
                    reason = self.ready(r, now)
                    if reason or not r.armed:
                        raise ValueError(reason or "请先解锁小车")
                    if r.owner != owner:
                        raise ValueError("另一控制页面已取得控制权")
                max_v, max_omega = self.limits(r)
                targets[ident] = (max(-max_v, min(max_v, cmd.v)),
                                  max(-max_omega, min(max_omega, cmd.omega)))
            for ident, r in robots.items():
                v, omega = targets[ident]
                if v or omega:
                    reason = None if self.allow_unlocalized_control else safety.check(self, r, v, omega, now, targets)
                    if reason:
                        raise ValueError(reason)
        except ValueError as exc:
            self.record("control", {"owner": owner, "requested": request, "accepted": False, "reason": str(exc)})
            for r in robots.values():
                if r.owner == owner:
                    self.stop(r, str(exc))
            raise
        packets = {}
        for ident, r in robots.items():
            cmd = commands[ident]
            v, omega = targets[ident]
            if not (v or omega) and not r.armed:
                # A zero-drive must never overtake an outstanding disarm packet.
                packets[ident] = self.stop(r, "已锁定") or self.packet(r, 0, 0, 100, "stop")
                continue
            r.target_v, r.target_omega = v, omega
            r.deadline = now+cmd.ttl_ms/1000 if v or omega else 0
            if r.owner == owner:
                r.owner_until = now+OWNER_TTL
            r.reason = "速度控制" if v or omega else "已停车"
            packets[ident] = self.packet(r, v, omega, cmd.ttl_ms)
        self.record("control", {"owner": owner, "requested": request, "accepted": True,
                                "applied": {ident: {"v": v, "omega": w} for ident, (v, w) in targets.items()}})
        return packets

    def limits(self, r):
        return (min(r.config.max_v, r.limits.max_v if r.limits else .10),
                min(r.config.max_omega, r.limits.max_omega if r.limits else .30))

    def stop(self, r, reason):
        self.record("stop", {"robot_id": r.config.id, "reason": reason})
        r.armed = False
        r.owner, r.owner_until = None, 0
        r.target_v = r.target_omega = 0
        r.deadline = 0
        r.reason = reason
        r.pending = None
        if self.mode == "demo":
            r.device_state = "disarmed"
            return self.packet(r, 0, 0, 100, "stop")
        else:
            r.bound = False
            return self.request(r, "stop", time.monotonic())

    def stop_all(self):
        self.estop = True
        for r in self.robots.values():
            self.stop(r, "全局停止")
        self.event("全局停止 · 所有小车已锁定")

    def tick(self, now):
        self.control_at = now
        for r in self.robots.values():
            reason = self.ready(r, now)
            if r.armed and not reason:
                if r.deadline and now >= r.deadline:
                    reason = "指令超时 · 已锁定"
                elif now >= r.owner_until:
                    reason = "控制权已过期 · 已锁定"
                elif r.target_v or r.target_omega:
                    reason = None if self.allow_unlocalized_control else safety.check(self, r, r.target_v, r.target_omega, now)
            if r.armed and reason:
                self.stop(r, reason)
                if "指令超时" in reason:
                    r.command_status = "expired"
                self.event(f"{r.config.name} · {reason}")
            if r.pending:
                action = r.pending["action"]
                if action == "arm" and (reason or now-r.pending_at > 1.):
                    self.stop(r, reason or "解锁确认超时 · 已锁定")
                if r.pending and now >= r.retry_at and now-r.seen_at <= HEARTBEAT_TTL:
                    # Same sequence retries do not renew a device motion watchdog.
                    r.pending["telemetry_seq"] = r.telemetry_seq
                    self.send(r.pending.copy(), r.endpoint)
                    r.retry_at = now+RETRY_INTERVAL

    def telemetry(self, msg: Telemetry, endpoint):
        r = self.robot(msg.robot_id)
        now = time.monotonic()
        if msg.boot_id in r.retired_boots:
            return
        new_boot = r.boot_id != msg.boot_id
        if not new_boot and msg.seq <= r.telemetry_seq:
            return
        reconnect = bool(r.seen_at and now-r.seen_at > HEARTBEAT_TTL)
        endpoint_changed = r.endpoint is not None and r.endpoint != endpoint
        if new_boot:
            if r.boot_id:
                r.retired_boots.add(r.boot_id)
            r.boot_id, r.ack_seq = msg.boot_id, -1
            r.bound, r.pending = False, None
        # Update the accepted telemetry BEFORE constructing any stop/arm packet.
        r.endpoint, r.telemetry_seq, r.seen_at = endpoint, msg.seq, now
        r.battery, r.voltage_v = msg.battery, msg.voltage_v
        r.measured_v, r.measured_omega = msg.measured_v, msg.measured_omega
        r.wheel_left, r.wheel_right = msg.wheel_left, msg.wheel_right
        r.encoder_left, r.encoder_right = msg.encoder_left, msg.encoder_right
        r.device_state, r.firmware, r.stop_reason = msg.device_state, msg.firmware, msg.stop_reason
        r.limits, r.fault = msg.limits, msg.fault
        self.record("telemetry", msg.model_dump())
        if new_boot or reconnect or endpoint_changed:
            r.bound = False
            self.stop(r, "设备连接 / 重连 · 等待停车确认")
            return
        current_ack = (msg.ack_session == self.session and msg.ack_seq is not None
                       and 0 <= msg.ack_seq <= r.seq)
        if current_ack:
            r.ack_seq = max(r.ack_seq, msg.ack_seq)
            if r.pending and msg.ack_seq >= r.pending["seq"]:
                if r.pending["action"] == "stop" and msg.device_state in ("disarmed", "fault"):
                    r.bound, r.pending = True, None
                    r.command_status = "confirmed"
                    r.reason = "已绑定 · 等待解锁"
                elif r.pending["action"] == "arm" and msg.device_state == "armed" and not r.fault:
                    r.pending, r.armed = None, True
                    r.command_status = "confirmed"
                    r.reason = "已解锁 · 等待指令"
            elif msg.ack_seq == r.seq:
                r.command_status = "confirmed"
        if msg.device_state == "unbound":
            r.bound = False
            if not (r.pending and r.pending["action"] == "stop"):
                self.stop(r, "车端链路恢复 · 等待停车确认")
        elif (r.armed or (r.pending and r.pending["action"] == "arm")) and (
                r.fault or (r.armed and msg.device_state != "armed")):
            self.stop(r, "车端已停机：" + (r.fault or r.stop_reason or "状态改变"))

    def pose(self, r, x, y, theta, at):
        if at <= r.pose_at:
            return
        dt = at-r.pose_at
        if r.x is not None and 0 < dt < POSE_TTL:
            raw = ((x-r.x)*math.cos(theta)+(y-r.y)*math.sin(theta))/dt
            old = r.estimated_v
            r.estimated_v = raw if old is None else .3*raw+.7*old
            r.acceleration = None if old is None else (r.estimated_v-old)/dt
        else:
            r.estimated_v = r.acceleration = None
        r.x, r.y, r.theta, r.pose_at = x, y, theta, at
        r.trail.append([round(x, 4), round(y, 4)])
        self.record("pose", {"robot_id": r.config.id, "x": x, "y": y, "theta": theta, "at": at})

    def snapshot(self):
        now = time.monotonic()
        robots = []
        for r in self.robots.values():
            visible = bool(r.pose_at and now-r.pose_at <= POSE_TTL)
            online = bool(r.seen_at and now-r.seen_at <= HEARTBEAT_TTL)
            corners = []
            if r.theta is not None:
                c, s = math.cos(r.theta), math.sin(r.theta)
                for dx, dy in [(1,1), (1,-1), (-1,-1), (-1,1)]:
                    x = dx*r.config.length/2+r.config.body_offset_x
                    y = dy*r.config.width/2+r.config.body_offset_y
                    corners.append([r.x+c*x-s*y, r.y+s*x+c*y])
            max_v, max_omega = self.limits(r)
            robots.append({"config": r.config.model_dump(), "x": r.x, "y": r.y, "theta": r.theta,
                "online": online, "visible": visible, "armed": r.armed, "bound": r.bound,
                "arm_pending": bool(r.pending and r.pending["action"] == "arm"),
                "control_owner": r.owner, "device_state": r.device_state, "firmware": r.firmware,
                "effective_max_v": max_v, "effective_max_omega": max_omega,
                "battery": r.battery, "voltage_v": r.voltage_v,
                "pose_age_ms": round((now-r.pose_at)*1000) if r.pose_at else None,
                "heartbeat_age_ms": round((now-r.seen_at)*1000) if r.seen_at else None,
                "measured_v": r.measured_v if online else None,
                "measured_omega": r.measured_omega if online else None,
                "wheel_left": r.wheel_left if online else None, "wheel_right": r.wheel_right if online else None,
                "encoder_left": r.encoder_left if online else None, "encoder_right": r.encoder_right if online else None,
                "estimated_v": r.estimated_v if visible else None,
                "acceleration": r.acceleration if visible else None,
                "target_v": r.target_v, "target_omega": r.target_omega,
                "seq": r.seq, "ack_seq": r.ack_seq, "command_status": r.command_status,
                "reason": r.reason, "fault": r.fault, "stop_reason": r.stop_reason,
                "corners": corners, "trail": list(r.trail)})
        return {"mode": self.mode, "session": self.session, "estop": self.estop,
                "allow_unlocalized_control": self.allow_unlocalized_control,
                "system_fault": self.runtime_fault,
                "timestamp": time.time(), "arena": {"width": self.settings.arena_width,
                "height": self.settings.arena_height}, "camera": self.camera,
                "robots": robots, "events": list(self.events)}
