"""Independent wire models. SI units; unknown sensor readings remain None."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResponseModel(BaseModel):
    # Keep new server fields accessible without coupling to backend internals.
    model_config = ConfigDict(extra="allow", frozen=True, allow_inf_nan=False)


class Velocity(BaseModel):
    """Body velocity: v in m/s, omega in rad/s (CCW positive), TTL in ms."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    v: float = Field(ge=-1, le=1)
    omega: float = Field(ge=-6, le=6)
    ttl_ms: int = Field(default=300, ge=100, le=500, strict=True)


class RobotConfig(ResponseModel):
    id: str
    name: str
    max_v: float
    max_omega: float


class RobotState(ResponseModel):
    config: RobotConfig
    x: float | None
    y: float | None
    theta: float | None
    online: bool
    visible: bool
    bound: bool
    armed: bool
    arm_pending: bool
    control_owner: str | None
    fault: str | None
    warning: str | None = None
    reason: str
    target_v: float
    target_omega: float
    measured_v: float | None
    measured_omega: float | None
    battery: float | None
    voltage_v: float | None
    wheel_left: float | None
    wheel_right: float | None
    encoder_left: int | None
    encoder_right: int | None
    estimated_v: float | None
    acceleration: float | None
    device_state: str | None
    firmware: str | None
    stop_reason: str | None
    pose_age_ms: float | None
    heartbeat_age_ms: float | None
    effective_max_v: float
    effective_max_omega: float
    seq: int
    ack_seq: int
    command_status: str

    @property
    def id(self) -> str:
        return self.config.id


class Arena(ResponseModel):
    width: float
    height: float


class State(ResponseModel):
    mode: Literal["demo", "hardware"]
    session: str
    timestamp: float
    estop: bool
    system_fault: str | None
    arena: Arena
    robots: list[RobotState]
    camera: dict[str, object]
    events: list[dict[str, object]]

    def robot(self, ident: str) -> RobotState:
        """Look up a robot by stable ID, not by list position."""
        for robot in self.robots:
            if robot.id == ident:
                return robot
        raise KeyError(ident)


class Health(ResponseModel):
    status: Literal["ok", "degraded"]
    mode: Literal["demo", "hardware"]
    ready: bool
    fault: str | None
    tasks: dict[str, str]
    vision_connected: bool
    run_id: str
    recording_error: str | None
    recording_dropped: int


class ArmResult(ResponseModel):
    armed: bool
    pending: bool


class ReleaseResult(ResponseModel):
    released: bool


class StopResult(ResponseModel):
    estop: bool


class CommandReceipt(ResponseModel):
    """Accepted/applied packet; this is not device ACK or measured motion."""

    version: int
    type: Literal["command"]
    session: str
    robot_id: str
    seq: int
    v: float
    omega: float
    ttl_ms: int
    action: str
    stop: bool
