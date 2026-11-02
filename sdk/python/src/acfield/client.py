"""Synchronous HTTP API with explicit commands and no automatic retries."""
from __future__ import annotations

import math
import re
import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING, TypeVar

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from .errors import APIError, ProtocolError, TransportError
from .models import (ArmResult, CommandReceipt, Health, ReleaseResult, State,
                     StopResult, Velocity)

if TYPE_CHECKING:
    from .control import ControlSession

T = TypeVar("T", bound=BaseModel)
_ROBOT_ID = re.compile(r"[a-zA-Z0-9_-]{1,32}\Z")


def robot_id(ident: str) -> str:
    if not isinstance(ident, str) or not _ROBOT_ID.fullmatch(ident):
        raise ValueError("Robot IDs must contain 1–32 letters, digits, underscores or hyphens")
    return ident


class Client:
    """ACField HTTP client. Use one instance per independent controller.

    Closing a client closes connections. Use ``control()`` to manage ownership.
    A timeout never retries a motion or arming request.
    """

    def __init__(self, url: str = "http://127.0.0.1:8000", *,
                 control_id: str | None = None, timeout: float = 0.5,
                 transport: httpx.BaseTransport | None = None):
        parsed = httpx.URL(url)
        if parsed.scheme not in ("http", "https") or not parsed.host or parsed.query or parsed.fragment:
            raise ValueError("url must be an HTTP(S) base URL without a query or fragment")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        if control_id is None:
            control_id = "python-" + uuid.uuid4().hex
        if not re.fullmatch(r"[!-~]{1,64}", control_id):
            raise ValueError("control_id must contain 1–64 printable ASCII characters without spaces")
        self._control_id = control_id
        self._control_active = False
        self._http = httpx.Client(base_url=url.rstrip("/") + "/",
                                  headers={"X-Control-ID": control_id}, timeout=timeout,
                                  transport=transport, follow_redirects=False)

    @property
    def control_id(self) -> str:
        return self._control_id

    def __enter__(self) -> Client:
        self._http.__enter__()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, *, json: object = None,
                 statuses: tuple[int, ...] = (200,)) -> object:
        if self._http.is_closed:
            raise TransportError("Client is closed")
        try:
            response = self._http.request(method, path.lstrip("/"), json=json)
        except httpx.RequestError as exc:
            raise TransportError(f"{method} {path}: {type(exc).__name__}: {exc}") from exc
        try:
            data = response.json()
        except ValueError as exc:
            if response.status_code not in statuses:
                raise APIError(response.status_code, response.text[:500], method, path) from exc
            raise ProtocolError(f"{method} {path}: expected a JSON response") from exc
        if response.status_code not in statuses:
            detail = data.get("detail", data) if isinstance(data, dict) else data
            raise APIError(response.status_code, detail, method, path)
        return data

    def _model(self, model: type[T], method: str, path: str, *,
               json: object = None, statuses: tuple[int, ...] = (200,)) -> T:
        data = self._request(method, path, json=json, statuses=statuses)
        try:
            return model.model_validate(data)
        except ValidationError as exc:
            raise ProtocolError(f"{method} {path}: invalid {model.__name__} response: {exc}") from exc

    def health(self) -> Health:
        """Return degraded health too; transport and malformed-response errors still raise."""
        return self._model(Health, "GET", "/api/health", statuses=(200, 503))

    def state(self) -> State:
        return self._model(State, "GET", "/api/state")

    def config(self) -> dict[str, object]:
        data = self._request("GET", "/api/config")
        if not isinstance(data, dict):
            raise ProtocolError("GET /api/config: expected an object")
        return data

    def arm(self, ident: str) -> ArmResult:
        """Request ownership and arming; hardware confirmation may still be pending."""
        return self._model(ArmResult, "POST", f"/api/robots/{robot_id(ident)}/arm",
                           json={"enabled": True})

    def disarm(self, ident: str) -> ArmResult:
        """Explicitly stop and lock this robot, regardless of its current owner."""
        return self._model(ArmResult, "POST", f"/api/robots/{robot_id(ident)}/arm",
                           json={"enabled": False})

    def release(self, ident: str) -> ReleaseResult:
        """Atomically stop/lock only if this client still owns the robot."""
        return self._model(ReleaseResult, "POST", f"/api/robots/{robot_id(ident)}/release")

    def command(self, ident: str, *, v: float, omega: float, ttl_ms: int = 300) -> CommandReceipt:
        velocity = Velocity(v=v, omega=omega, ttl_ms=ttl_ms)
        return self._model(CommandReceipt, "POST", f"/api/robots/{robot_id(ident)}/command",
                           json=velocity.model_dump())

    def commands(self, actions: Mapping[str, Velocity]) -> dict[str, CommandReceipt]:
        if not 1 <= len(actions) <= 16:
            raise ValueError("A joint action must contain 1–16 robots")
        payload = {}
        for ident, velocity in actions.items():
            robot_id(ident)
            if not isinstance(velocity, Velocity):
                raise TypeError("Use Velocity(v=..., omega=...) for each joint action")
            payload[ident] = velocity.model_dump()
        data = self._request("POST", "/api/commands", json=payload)
        try:
            receipts = TypeAdapter(dict[str, CommandReceipt]).validate_python(data)
        except ValidationError as exc:
            raise ProtocolError(f"POST /api/commands: invalid command receipts: {exc}") from exc
        if set(receipts) != set(actions) or any(r.robot_id != ident for ident, r in receipts.items()):
            raise ProtocolError("POST /api/commands: response robot IDs do not match the request")
        return receipts

    def stop_all(self) -> StopResult:
        """Activate global stop and lock every robot, including other controllers' robots."""
        return self._model(StopResult, "POST", "/api/stop")

    def reset_stop(self) -> StopResult:
        """Explicitly release global stop; robots remain disarmed."""
        return self._model(StopResult, "POST", "/api/reset-stop")

    def control(self, *robots: str, allow_hardware: bool = False,
                arm_timeout: float = 1.5) -> ControlSession:
        from .control import ControlSession
        return ControlSession(self, robots, allow_hardware=allow_hardware, arm_timeout=arm_timeout)
