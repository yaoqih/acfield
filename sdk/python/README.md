# ACField Python SDK

A small, typed, synchronous client for the ACField multi-robot control server.
Python 3.11+. Distribution and import name: `acfield`. Development preview.

## Install

From the repository root, into your algorithm's virtual environment:

```bash
python -m pip install ./sdk/python
# Development
python -m pip install -e './sdk/python[test]'
```

Or pin a Git commit without cloning the repository yourself:

```bash
python -m pip install 'acfield @ git+https://github.com/yaoqih/acfield.git@main#subdirectory=sdk/python'
```

Replace `main` with the full tested commit for reproducible experiments. The package
has not been published to PyPI; plain `pip install acfield` is not an installation
instruction for this project. It does not require the server, frontend or firmware
dependencies on the client computer.

## Read state

```python
from acfield import Client

with Client("http://127.0.0.1:8000") as client:
    health = client.health()
    state = client.state()
    robot = state.robot("car-01")
    print(health.mode, robot.x, robot.y, robot.theta, robot.reason)
```

Core responses are typed Pydantic models. Unknown measurements stay `None`. New
server fields remain available through `model_dump()` and model extras.

## Scoped multi-robot control

Start the ACField demo server first. This example sends new joint actions explicitly
at about 10 Hz, for two seconds:

```python
import time
from acfield import Client, Velocity

with Client() as client:
    with client.control("car-01", "car-02") as control:
        end = time.monotonic() + 2.0
        while time.monotonic() < end:
            tick = time.monotonic()
            state = control.state()
            # Replace these velocities with your policy(state).
            receipts = control.commands({
                ident: Velocity(v=0.05, omega=0.0, ttl_ms=300)
                for ident in control.robots
            })
            time.sleep(max(0.0, min(0.1 - (time.monotonic() - tick),
                                    end - time.monotonic())))
```

`control()` checks health, mode, selected-robot readiness and existing ownership,
requests arming, then waits for confirmation. It refuses hardware mode unless
`allow_hardware=True` is explicit. It never releases global stop automatically.
Commands check a fresh snapshot and keep one `X-Control-ID` for the client lifetime.
The server remains the final authority on ownership and interlocks.

Normal exit, exceptions, Ctrl+C and partial acquisition request conditional release
of attempted robots. The server checks ownership and stops in one operation, so
cleanup does not stop a new owner. This requires the accompanying server revision
with `/api/robots/{id}/release`; an older server returns a visible cleanup error.
Physical stop confirmation still requires telemetry and measured feedback.

## Explicit operations

| Method | Meaning |
| --- | --- |
| `health()` / `state()` / `config()` | Read service health, typed state or configuration |
| `arm(id)` | Request ownership and arming; inspect `armed` / `pending` |
| `command(id, v=..., omega=..., ttl_ms=300)` | Submit a single velocity |
| `commands({id: Velocity(...)})` | Submit a jointly validated batch |
| `release(id)` | Stop and lock only if this client still owns the robot |
| `disarm(id)` | Explicitly stop and lock a robot, regardless of owner |
| `stop_all()` | Activate global stop for every robot |
| `reset_stop()` | Explicitly release global stop; robots remain locked |

Velocities use m/s and rad/s, counterclockwise positive. TTL is 100–500 ms.
Receipts report the server's applied/clamped velocity, not device acknowledgement
or measured physical motion. Check state and experiment logs for those facts.

There are no automatic motion retries, background heartbeats or command renewal.
A slow or failed policy must expire rather than keep an old command alive. Use a
fresh result and observation age when integrating slow inference.

`Client.close()` only closes HTTP connections. Use `control()` for managed cleanup,
or explicitly `release()` after low-level `arm()`. Do not overlap managed sessions
on the same client; use a new client/control ID for each independent controller.

## Errors and limits

- `APIError`: HTTP rejection with `status_code`, `detail`, `method` and `path`.
- `TransportError`: connection/timeout failure; the request may have reached the server.
- `ProtocolError`: malformed successful response or an incompatible server.
- `ControlError`: failed preflight, lost ownership/arming or changed server session.
- `CleanupError`: one or more release requests failed. Cleanup attempts every robot;
  if a policy exception is already active, that exception is preserved with a note
  and a warning. Inspect the console; client cleanup is best effort.
- Invalid local arguments raise `ValueError` (including Pydantic `ValidationError`).

`health()` returns a typed degraded response for HTTP 503 so callers can inspect it.
The default timeout is 0.5 seconds per HTTPX network phase, not a hard end-to-end
deadline. `arm_timeout` bounds confirmation polling and can be exceeded by an
in-flight HTTP request. Forced termination or a disconnected network relies on
server/device watchdogs, whose physical stopping behavior must be measured.

This release is synchronous HTTP. WebSocket subscriptions, an async client, episode
management and training-environment adapters are outside the current SDK.

## Test

From the repository root:

```bash
python -m pip install -e './robot_server[test]' -e './sdk/python[test]'
python -m pytest sdk/python/tests -q
```

Tests exercise the actual demo API, lifecycle and ownership races, partial failure,
timeout outcomes, device-confirmation polling, TTL expiry and response validation.

See the [SDK guide](https://yaoqih.github.io/acfield/guide/python-sdk) and
[platform repository](https://github.com/yaoqih/acfield). Apache-2.0; see the root
LICENSE. Maintained by AClab.
