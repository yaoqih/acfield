"""Single event-loop owner for state, handshakes and motion interlocks."""
import math
import os
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from .models import Command, DeviceLimits, RobotConfig, Settings, Telemetry
from . import safety
from .clock import clock

POSE_TTL = .2
HEARTBEAT_TTL = 3.
RETRY_INTERVAL = .15
OWNER_TTL = 10.
DIAGNOSTIC_HEARTBEAT_TTL = 3.
DIAGNOSTIC_RUN_SECONDS = 120.
# Versioned mappings prevent showing full duty on older firmware capped at 35.
DIAGNOSTIC_PROFILES = {"0.2.3-encoder-diagnostic": 35, "0.2.4-encoder-diagnostic": 255,
                       "0.2.5-encoder-diagnostic": 255}
DIAGNOSTIC_PWM_PER_MPS = 350


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
    last_stop_reason: str | None = None
    limits: DeviceLimits | None = None
    owner: str | None = None
    owner_until: float = 0
    target_v: float = 0
    target_omega: float = 0
    deadline: float = 0
    deferred_command: Command | None = None
    deferred_until: float = 0
    diagnostic_hold: Command | None = None
    diagnostic_until: float = 0
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
    warning: str | None = None
    applied_seq: int | None = None
    motion_echo_rejections: int | None = None
    sampled_at_ms: float | None = None
    clock_synced: bool = False
    clock_uncertainty_ms: float | None = None
    reason: str = "等待设备连接"
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
        self.events.appendleft({"time": clock.now_ms()/1000, "message": message})
        self.record("event", {"message": message})

    def robot(self, ident):
        return self.robots[ident]

    def heartbeat_ttl(self, r):
        return DIAGNOSTIC_HEARTBEAT_TTL if r.firmware in DIAGNOSTIC_PROFILES else HEARTBEAT_TTL

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
        if not r.seen_at or now-r.seen_at > self.heartbeat_ttl(r):
            return "设备离线"
        if not r.bound:
            return "等待车端停车绑定确认，请确认固件已更新"
        if not self.allow_unlocalized_control and (not r.pose_at or now-r.pose_at > POSE_TTL):
            return "定位已过期"
        return None

    def arm(self, r, enabled, owner="local"):
        if not enabled:
            self.stop(r, "已停车")
            return
        now = time.monotonic()
        reason = self.ready(r, now)
        if reason:
            raise ValueError(reason)
        if r.owner and r.owner != owner:
            raise ValueError("另一控制页面已取得控制权，请先停车")
        if r.armed or (r.pending and r.pending["action"] == "arm"):
            return
        r.owner, r.owner_until = owner, now+OWNER_TTL
        if self.mode == "demo":
            r.armed, r.device_state = True, "armed"
            r.reason = "控制就绪"
        else:
            self.request(r, "arm", now)
            r.reason = "正在准备控制"
        self.event(f"{r.config.name} · 准备控制")

    def release(self, r, owner, reason="控制源已释放 · 已停车"):
        """Check and release in one event-loop operation; never stop a new owner."""
        if r.owner != owner:
            return False
        self.stop(r, reason)
        return True

    def packet(self, r, v, omega, ttl_ms, action="drive", execute_at_ms=None, immediate=False):
        r.seq += 1
        packet = {"version": 1, "type": "command", "session": self.session,
                  "robot_id": r.config.id, "boot_id": r.boot_id, "telemetry_seq": r.telemetry_seq,
                  "seq": r.seq, "v": v, "omega": omega, "action": action,
                  "ttl_ms": ttl_ms, "stop": v == 0 and omega == 0}
        if not immediate and r.clock_synced and action == "drive" and (v or omega):
            packet["execute_at_ms"] = execute_at_ms if execute_at_ms is not None else clock.now_ms()+60
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
                if cmd.hold and not cmd.immediate:
                    raise ValueError("持续诊断必须使用立即执行的 PWM 指令")
                if cmd.immediate:
                    profile = self.encoder_diagnostic(r)
                    if profile is None:
                        raise ValueError("立即执行仅适用于支持的编码器诊断固件")
                    if cmd.execute_at_ms is not None:
                        raise ValueError("立即执行不能同时设置执行时间")
                    if cmd.omega or abs(cmd.v)*DIAGNOSTIC_PWM_PER_MPS > profile["max_pwm"]+1e-6:
                        raise ValueError("诊断指令须为双轮直行，且不能超过 PWM 上限")
                if cmd.v or cmd.omega or cmd.hold:
                    if cmd.execute_at_ms is not None and self.mode == "hardware" and not r.clock_synced:
                        raise ValueError("等待车端时钟同步")
                    if cmd.execute_at_ms is not None and not 15 <= cmd.execute_at_ms-clock.now_ms() <= 150:
                        raise ValueError("控制指令执行时间已过期或超出缓冲窗口")
                    reason = self.ready(r, now)
                    if reason:
                        raise ValueError(reason)
                    if r.owner and r.owner != owner:
                        raise ValueError("另一控制页面已取得控制权")
                if cmd.immediate:
                    # Diagnostic transport v is PWM/350, not a physical speed.
                    targets[ident] = (cmd.v, cmd.omega)
                else:
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
            if (v or omega or cmd.hold) and not r.armed:
                # First fresh input claims control and performs the device arm
                # handshake. Keep only the latest input within its original TTL.
                self.arm(r, True, owner)
                if not r.armed:
                    r.deferred_command = cmd.model_copy(deep=True)
                    r.deferred_until = now+cmd.ttl_ms/1000
                    packets[ident] = r.pending.copy()
                    continue
            if not (v or omega or cmd.hold) and not r.armed:
                # A zero-drive must never overtake an outstanding disarm packet.
                packets[ident] = self.stop(r, "已停车") or self.packet(r, 0, 0, 100, "stop")
                continue
            r.target_v, r.target_omega = v, omega
            if cmd.hold:
                if r.diagnostic_hold is None:
                    r.diagnostic_until = now+DIAGNOSTIC_RUN_SECONDS
                r.diagnostic_hold = cmd.model_copy(deep=True)
            else:
                r.diagnostic_hold, r.diagnostic_until = None, 0
            r.deadline = now+cmd.ttl_ms/1000 if v or omega else 0
            if r.owner == owner:
                r.owner_until = now+OWNER_TTL
            r.reason = ("诊断 PWM 控制" if cmd.immediate else "速度控制") if v or omega else "已停车"
            packets[ident] = self.packet(r, v, omega, cmd.ttl_ms, execute_at_ms=cmd.execute_at_ms,
                                         immediate=cmd.immediate)
        self.record("control", {"owner": owner, "requested": request, "accepted": True,
                                "applied": {ident: {"v": v, "omega": w} for ident, (v, w) in targets.items()}})
        return packets

    def limits(self, r):
        if self.mode == "demo":
            return r.config.max_v, r.config.max_omega
        return (min(r.config.max_v, r.limits.max_v if r.limits else .10),
                min(r.config.max_omega, r.limits.max_omega if r.limits else .30))

    def encoder_diagnostic(self, r):
        max_pwm = DIAGNOSTIC_PROFILES.get(r.firmware)
        if max_pwm is None:
            return None
        if r.limits:
            max_pwm = min(max_pwm, math.floor(r.limits.max_v*DIAGNOSTIC_PWM_PER_MPS+1e-3))
        return {"max_pwm": max_pwm, "pwm_per_mps": DIAGNOSTIC_PWM_PER_MPS}

    def stop(self, r, reason):
        self.record("stop", {"robot_id": r.config.id, "reason": reason})
        r.last_stop_reason = reason
        r.armed = False
        r.owner, r.owner_until = None, 0
        r.target_v = r.target_omega = 0
        r.deadline = 0
        r.deferred_command, r.deferred_until = None, 0
        r.diagnostic_hold = None
        r.diagnostic_until = 0
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
            if r.deferred_command and now >= r.deferred_until:
                self.stop(r, "等待控制确认时指令已过期 · 已停车")
            if r.armed and not reason:
                if r.diagnostic_hold and now >= r.diagnostic_until:
                    reason = "达到 120 秒运行上限 · 已停车"
                elif not r.diagnostic_hold and r.deadline and now >= r.deadline:
                    reason = "指令超时 · 已停车"
                elif not r.diagnostic_hold and now >= r.owner_until:
                    reason = "控制权已过期 · 已停车"
                elif r.target_v or r.target_omega:
                    reason = None if self.allow_unlocalized_control else safety.check(self, r, r.target_v, r.target_omega, now)
            if r.armed and reason:
                self.stop(r, reason)
                if "指令超时" in reason:
                    r.command_status = "expired"
                self.event(f"{r.config.name} · {reason}")
            if r.armed and not reason and r.diagnostic_hold:
                cmd = r.diagnostic_hold
                profile = self.encoder_diagnostic(r)
                if not profile or abs(cmd.v)*DIAGNOSTIC_PWM_PER_MPS > profile["max_pwm"]+1e-6:
                    self.stop(r, "诊断固件或 PWM 上限已变化")
                else:
                    r.owner_until = now+OWNER_TTL
                    r.deadline = now+cmd.ttl_ms/1000 if cmd.v else 0
                    self.packet(r, cmd.v, 0, cmd.ttl_ms, immediate=True)
            if r.pending:
                action = r.pending["action"]
                if action == "arm" and (reason or now-r.pending_at > 1.):
                    self.stop(r, reason or "控制准备确认超时 · 已停车")
                if r.pending and now >= r.retry_at and now-r.seen_at <= self.heartbeat_ttl(r):
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
        gap_ms = round((now-r.seen_at)*1000) if r.seen_at else 0
        reconnect = bool(r.seen_at and now-r.seen_at > self.heartbeat_ttl(r))
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
        r.warning = msg.warning
        r.applied_seq, r.sampled_at_ms = msg.applied_seq, msg.sampled_at_ms
        r.motion_echo_rejections = msg.motion_echo_rejections
        r.clock_synced = msg.clock_synced
        r.clock_uncertainty_ms = msg.clock_uncertainty_ms
        self.record("telemetry", msg.model_dump())
        if new_boot or reconnect or endpoint_changed:
            r.bound = False
            cause = ("设备启动 ID 已变化" if new_boot else
                     "设备通信地址已变化" if endpoint_changed else f"遥测中断 {gap_ms} ms 后恢复")
            self.stop(r, cause+" · 等待停车确认")
            return
        current_ack = (msg.ack_session == self.session and msg.ack_seq is not None
                       and 0 <= msg.ack_seq <= r.seq)
        if current_ack:
            r.ack_seq = max(r.ack_seq, msg.ack_seq)
            if r.pending and msg.ack_seq >= r.pending["seq"]:
                if r.pending["action"] == "stop" and msg.device_state in ("disarmed", "fault"):
                    r.bound, r.pending = True, None
                    r.command_status = "confirmed"
                    r.reason = "准备就绪 · 可直接控制"
                elif r.pending["action"] == "arm" and msg.device_state == "armed" and not r.fault:
                    r.pending, r.armed = None, True
                    r.command_status = "confirmed"
                    r.reason = "控制就绪"
                    cmd, until = r.deferred_command, r.deferred_until
                    r.deferred_command, r.deferred_until = None, 0
                    if cmd is not None:
                        remaining = math.floor((until-now)*1000)
                        if remaining < 100:
                            self.stop(r, "等待控制确认时指令已过期 · 已停车")
                        else:
                            # Recompute scheduled execution after the handshake;
                            # waiting must never renew the input's lifetime.
                            cmd = cmd.model_copy(update={"ttl_ms": remaining, "execute_at_ms": None})
                            try:
                                self.command(r, cmd, r.owner)
                            except ValueError:
                                pass  # commands() already records and stops the owner.
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
            online = bool(r.seen_at and now-r.seen_at <= self.heartbeat_ttl(r))
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
                "encoder_diagnostic": self.encoder_diagnostic(r),
                "diagnostic_running": r.diagnostic_hold is not None,
                "diagnostic_remaining_ms": max(0, round((r.diagnostic_until-now)*1000)) if r.diagnostic_hold else None,
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
                "clock_synced": r.clock_synced, "clock_uncertainty_ms": r.clock_uncertainty_ms,
                "applied_seq": r.applied_seq, "sampled_at_ms": r.sampled_at_ms,
                "motion_echo_rejections": r.motion_echo_rejections,
                "seq": r.seq, "ack_seq": r.ack_seq, "command_status": r.command_status,
                "reason": r.reason, "fault": r.fault, "warning": r.warning, "stop_reason": r.stop_reason,
                "last_stop_reason": r.last_stop_reason,
                "corners": corners, "trail": list(r.trail)})
        return {"mode": self.mode, "session": self.session, "estop": self.estop,
                "allow_unlocalized_control": self.allow_unlocalized_control,
                "system_fault": self.runtime_fault,
                "timestamp": clock.now_ms()/1000, "clock": clock.status(), "arena": {"width": self.settings.arena_width,
                "height": self.settings.arena_height}, "camera": self.camera,
                "robots": robots, "events": list(self.events)}
