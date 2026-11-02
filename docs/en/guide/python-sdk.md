# Python SDK

The SDK packages HTTP requests, typed responses, ownership and cleanup so algorithm code can focus on reading state and producing actions. Its distribution and import name is `acfield`. Source lives in `sdk/python/` and is maintained with the server but installed separately.

This **0.1.0 development preview** provides synchronous HTTP and a managed control lifecycle. It does not depend on backend implementation, the frontend, PlatformIO, NumPy or a training framework.

## Installation {#installation}

From the repository root, in your algorithm's virtual environment:

```bash
python -m pip install ./sdk/python

# Editable installation for SDK development
python -m pip install -e './sdk/python[test]'
```

To reuse the server environment, run from the root:

```bash
uv pip install --python robot_server/.venv/bin/python -e ./sdk/python
robot_server/.venv/bin/python examples/velocity_control.py --robots car-01 car-02 --duration 2
```

You can also install directly from Git:

```bash
python -m pip install 'acfield @ git+https://github.com/yaoqih/acfield.git@main#subdirectory=sdk/python'
```

For reproducibility, replace `main` with the full tested commit SHA. The package has not been published to PyPI; use local or Git installation.

## Read-only state {#read-only-state}

```python
from acfield import Client

with Client("http://127.0.0.1:8000") as client:
    health = client.health()
    state = client.state()
    robot = state.robot("car-01")
    print(health.mode, robot.x, robot.y, robot.theta)
    print(robot.measured_v, robot.command_status, robot.reason)
```

`State`, `RobotState`, `Health` and command receipts provide type hints and response validation. Look up robots by stable ID, not list position. Unknown measurements remain `None`. New server fields remain accessible through `model_dump()`.

`health()` returns typed `status="degraded"` health for a server 503 response so callers can inspect it. Network failures and malformed responses still raise. Health's `ready` concerns all configured robots; a control session checks its selected subset.

## A two-robot control loop {#a-two-robot-control-loop}

Start the [demo server](./quickstart), then run:

```python
import time
from acfield import Client, Velocity

with Client() as client:
    with client.control("car-01", "car-02") as control:
        end = time.monotonic() + 2.0
        while time.monotonic() < end:
            tick = time.monotonic()
            state = control.state()
            # Replace with new actions from policy(state).
            actions = {
                ident: Velocity(v=0.05, omega=0.0, ttl_ms=300)
                for ident in control.robots
            }
            receipts = control.commands(actions)
            time.sleep(max(0.0, min(0.1 - (time.monotonic() - tick),
                                    end - time.monotonic())))
```

This explicitly sends a new action about every 100 ms with a 300 ms TTL for two seconds. `v` is m/s and `omega` is rad/s, counterclockwise positive. Schema limits are not recommended hardware speeds; the server further clamps to effective robot limits. Receipts report accepted/clamped values.

The example reads global state. Observation and message constraints still belong to the experiment layer. Do not expose global snapshots to policies claimed to use local information only.

## What a control session does {#what-a-control-session-does}

Entering `with client.control(...)` checks service health, mode, selected robots' binding, online/localization status and faults. It rejects existing owners, requests arming individually, then waits for `armed=true` with the matching control ID. Entering the body means confirmation is recorded by the server.

`control.state()` checks a fresh snapshot. `control.commands()` also checks fresh state and limits targets to selected robots. The server remains authoritative for ownership, TTL, boundaries and spacing. A changed server session or lost arming raises rather than silently reacquiring control.

Normal exit, exceptions, Ctrl+C and partial acquisition all attempt conditional release of robots whose arming was attempted. `POST /api/robots/{id}/release` checks ownership and stops in one event-loop operation, eliminating the race between reading ownership and disarming. A robot no longer owned by this client returns `released=false`.

::: tip Lifecycle boundary
`Client.close()` only closes connections. Use `control()` for managed release, or explicitly pair low-level `arm()` with `release()`. Use separate clients for independent controllers and do not share control IDs or overlap managed sessions on one client.
:::

An accepted release is not measured physical stopping. Inspect device ACK, wheel speed and visual feedback. Forced termination, network loss or an unreachable server may prevent cleanup delivery; stopping then depends on server/device watchdogs.

## Explicit hardware selection {#explicit-hardware-selection}

```python
with Client("http://127.0.0.1:8000") as client:
    with client.control("car-01", allow_hardware=True, arm_timeout=1.5) as control:
        state = control.state()
        # Send new, bounded actions after calibration and acceptance.
```

Sessions refuse hardware by default and never release global stop automatically. `allow_hardware=True` explicitly selects real mode; it does not replace [bring-up](../hardware/bringup). Low-level `arm()` and explicit stops directly follow server semantics without mode gating.

## API overview {#api-overview}

| Method | Return / meaning |
| --- | --- |
| `client.health()` | `Health`, including degraded responses |
| `client.state()` | `State`; `state.robot(id)` looks up by ID |
| `client.config()` | Configuration dictionary |
| `client.arm(id)` | `ArmResult`, possibly still pending |
| `client.command(id, v=..., omega=..., ttl_ms=300)` | One `CommandReceipt` |
| `client.commands({id: Velocity(...)})` | ID-to-receipt map for a jointly validated batch |
| `client.release(id)` | Stop/disarm only if still owned by this client |
| `client.disarm(id)` | Explicit stop/disarm, regardless of owner |
| `client.stop_all()` | Activate global stop and lock all robots |
| `client.reset_stop()` | Explicitly release global stop; robots stay disarmed |
| `client.control(*ids, ...)` | Confirm arming, monitor conditions and release on exit |

Receipts are server-accepted command packets, not device ACK or measured motion. `seq/ack_seq/command_status` and measured fields provide different evidence; see the [API reference](../reference/api).

## Errors, timeouts and renewal {#errors-timeouts-and-renewal}

| Error | Meaning |
| --- | --- |
| `APIError` | HTTP rejection, retaining `status_code/detail/method/path` |
| `TransportError` | Connection/timeout; server outcome may be unknown |
| `ProtocolError` | Successful response did not match the expected format |
| `ControlError` | Preconditions, arming, ownership or server session changed |
| `CleanupError` | One or more conditional releases failed |
| `ValueError` / Pydantic `ValidationError` | Invalid local arguments before networking |

SDK runtime errors inherit `ACFieldError`. Cleanup continues across other robots if one release fails. An active policy exception is preserved with an added note and warning. Do not swallow cleanup errors and assume stopping was confirmed.

The default `timeout=0.5` is an HTTPX per-network-phase timeout, not a hard real-time deadline. `arm_timeout` bounds confirmation polling, but an in-flight request can add a request timeout.

There are no automatic motion/arming retries or background renewal threads. Blocked policies should expire through TTL. Reconnection and restored localization do not resume motion. Slow inference needs explicit observation times, result lifetimes and new actions.

Use this SDK with the accompanying server revision. Conditional release requires the new `/release` endpoint; older servers fail visibly rather than falling back to a racy disarm. WebSocket, async clients and training adapters await concrete needs.

## Design and validation {#design-and-validation}

Independent packaging keeps the algorithm environment dependent only on HTTPX and Pydantic. Shared-repository maintenance lets server and SDK protocol changes be reviewed together. Managed sessions cover common lifecycle operations while low-level methods preserve HTTP semantics, with no policy base classes or hidden schedulers.

Tests use the actual control API and cover multi-robot ownership, races, partial failure, uncertain timeout outcomes, device-confirmation polling, TTL and response errors. CI installs the packaged SDK on Python 3.11, 3.12 and 3.13.

```bash
# Repository root, in a development environment
python -m pip install -e './robot_server[test]' -e './sdk/python[test]'
python -m pytest sdk/python/tests -q
```
