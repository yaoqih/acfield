"""Explicit, scoped ownership with confirmation and conditional cleanup."""
from __future__ import annotations

import math
import time
import warnings
from collections.abc import Mapping
from typing import TYPE_CHECKING

from .client import robot_id
from .errors import ACFieldError, CleanupError, ControlError
from .models import CommandReceipt, State, Velocity

if TYPE_CHECKING:
    from .client import Client


class ControlSession:
    """A single-use context manager; no background threads or command renewal."""

    def __init__(self, client: Client, robots: tuple[str, ...], *,
                 allow_hardware: bool, arm_timeout: float):
        if not 1 <= len(robots) <= 16 or len(robots) != len(set(robots)):
            raise ValueError("Select 1–16 unique robot IDs")
        for ident in robots:
            robot_id(ident)
        if not math.isfinite(arm_timeout) or arm_timeout <= 0:
            raise ValueError("arm_timeout must be finite and positive")
        self._client = client
        self.robots = robots
        self._allow_hardware = allow_hardware
        self._arm_timeout = arm_timeout
        self._attempted: list[str] = []
        self._session: str | None = None
        self._active = False
        self._used = False

    def _check(self, state: State, *, owned: bool) -> None:
        if state.session != self._session:
            raise ControlError("Server session changed; do not silently resume control")
        if state.estop or state.system_fault:
            raise ControlError(f"Global stop or system fault is active: {state.system_fault}")
        for ident in self.robots:
            try:
                robot = state.robot(ident)
            except KeyError as exc:
                raise ControlError(f"Unknown robot: {ident}") from exc
            if not (robot.bound and robot.online and robot.visible) or robot.fault:
                raise ControlError(f"{ident} is not ready: {robot.fault or robot.reason}")
            if owned and (not robot.armed or robot.control_owner != self._client.control_id):
                raise ControlError(f"{ident} lost arming or ownership: {robot.reason}")

    def __enter__(self) -> ControlSession:
        if self._used:
            raise ControlError("A control session can only be entered once")
        if self._client._control_active:
            raise ControlError("Use a separate Client for an overlapping control session")
        self._used = True
        self._client._control_active = True
        try:
            health = self._client.health()
            if health.status != "ok":
                raise ControlError(f"Service health is degraded: {health.fault}")
            if health.mode != "demo" and not self._allow_hardware:
                raise ControlError("Hardware mode requires allow_hardware=True after calibration and bring-up")
            initial = self._client.state()
            self._session = initial.session
            # Recheck mode in case the server restarted after health().
            if initial.mode != health.mode:
                raise ControlError("Server mode changed during preflight")
            self._check(initial, owned=False)
            for ident in self.robots:
                if initial.robot(ident).control_owner is not None or initial.robot(ident).armed:
                    raise ControlError(f"{ident} already has an owner or is armed; release it first")
            for ident in self.robots:
                # A timed-out arm request may have acquired ownership on the server.
                self._attempted.append(ident)
                self._client.arm(ident)
            deadline = time.monotonic() + self._arm_timeout
            while True:
                state = self._client.state()
                self._check(state, owned=False)
                selected = [state.robot(ident) for ident in self.robots]
                if any(r.control_owner != self._client.control_id for r in selected):
                    raise ControlError("Ownership lost while waiting for arming confirmation")
                if all(r.armed for r in selected):
                    self._active = True
                    return self
                if any(not r.arm_pending for r in selected if not r.armed):
                    raise ControlError("Arming was cancelled by the server or device")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ControlError("Timed out waiting for device arming confirmation")
                time.sleep(min(0.05, remaining))
        except BaseException as exc:
            self._cleanup(exc)
            raise

    def state(self) -> State:
        """Read a fresh snapshot and verify all selected robots remain controllable."""
        if not self._active:
            raise ControlError("Control session is not active")
        state = self._client.state()
        self._check(state, owned=True)
        return state

    def commands(self, actions: Mapping[str, Velocity]) -> dict[str, CommandReceipt]:
        if not set(actions).issubset(self.robots):
            raise ValueError("Actions may only target robots selected by this session")
        self.state()
        return self._client.commands(actions)

    def command(self, ident: str, *, v: float, omega: float, ttl_ms: int = 300) -> CommandReceipt:
        return self.commands({ident: Velocity(v=v, omega=omega, ttl_ms=ttl_ms)})[ident]

    def _cleanup(self, original: BaseException | None) -> None:
        self._active = False
        failures = {}
        for ident in self._attempted:
            try:
                # The server checks ownership and stops in one event-loop operation.
                self._client.release(ident)
            except ACFieldError as exc:
                failures[ident] = exc
        self._attempted.clear()
        self._client._control_active = False
        if failures:
            error = CleanupError(failures)
            if original is None:
                raise error
            original.add_note(str(error))
            warnings.warn(str(error), RuntimeWarning, stacklevel=3)

    def __exit__(self, exc_type: object, exc: BaseException | None, traceback: object) -> None:
        self._cleanup(exc)
