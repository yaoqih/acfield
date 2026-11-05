"""Wire contracts. Distances in metres, angles in radians, CCW positive."""
from typing import Literal
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class RobotConfig(Model):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,32}$")
    name: str = Field(min_length=1, max_length=40)
    tag_id: int = Field(ge=0, le=65535)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    tag_size: float = Field(default=.104, gt=0, le=1)
    tag_height: float = Field(default=.0646, ge=0, le=10)
    length: float = Field(default=.20, gt=0, le=1)
    width: float = Field(default=.16, gt=0, le=1)
    body_offset_x: float = Field(default=0, ge=-1, le=1)
    body_offset_y: float = Field(default=0, ge=-1, le=1)
    # Tag centre in the robot body frame (x forward, y left).
    tag_offset_x: float = Field(default=0, ge=-1, le=1)
    tag_offset_y: float = Field(default=0, ge=-1, le=1)
    heading_offset: float = Field(default=0, ge=-3.142, le=3.142)
    max_v: float = Field(default=1.0, gt=0, le=1)
    max_omega: float = Field(default=3.00, gt=0, le=6)


class Settings(Model):
    vision_url: str = Field(default="", max_length=2048)
    arena_width: float = Field(default=3, ge=1, le=20)
    arena_height: float = Field(default=3, ge=1, le=20)
    robots: list[RobotConfig] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def unique_ids(self):
        if self.vision_url:
            url = urlparse(self.vision_url)
            if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError('视觉服务地址必须是无账号、查询参数的 HTTP(S) 地址')
            self.vision_url = self.vision_url.rstrip('/')
        for key in ("id", "tag_id"):
            values = [getattr(r, key) for r in self.robots]
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate {key}")
        return self


class Command(Model):
    v: float = Field(ge=-1, le=1)
    omega: float = Field(ge=-6, le=6)
    ttl_ms: int = Field(default=300, ge=100, le=500)


class DeviceLimits(Model):
    max_v: float = Field(gt=0, le=1)
    max_omega: float = Field(gt=0, le=6)


class Telemetry(Model):
    version: Literal[1]
    type: Literal["telemetry"]
    robot_id: str
    boot_id: str = Field(min_length=1, max_length=64)
    seq: int = Field(ge=0)
    battery: float | None = Field(default=None, ge=0, le=100)
    measured_v: float | None = Field(default=None, ge=-3, le=3)
    measured_omega: float | None = Field(default=None, ge=-30, le=30)
    ack_session: str | None = None
    ack_seq: int | None = Field(default=None, ge=0)
    fault: str | None = Field(default=None, max_length=120)
    device_state: Literal["unbound", "disarmed", "armed", "fault"] | None = None
    firmware: str | None = Field(default=None, max_length=40)
    stop_reason: str | None = Field(default=None, max_length=80)
    voltage_v: float | None = Field(default=None, ge=0, le=30)
    wheel_left: float | None = Field(default=None, ge=-3, le=3)
    wheel_right: float | None = Field(default=None, ge=-3, le=3)
    encoder_left: int | None = None
    encoder_right: int | None = None
    limits: DeviceLimits | None = None


def default_settings():
    return Settings(robots=[RobotConfig(id=f"car-{i+1:02}", name=name, tag_id=10+i, color=color)
        for i, (name, color) in enumerate([
            ("追捕车 A", "#28786b"), ("追捕车 B", "#427dc2"),
            ("追捕车 C", "#ac7b35"), ("逃逸车 D", "#ba6070")])])
