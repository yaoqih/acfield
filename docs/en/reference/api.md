# HTTP and WebSocket

The control service defaults to `http://127.0.0.1:8000`. Runtime OpenAPI is available at `/docs`; this page describes the main semantics.

## Endpoints {#endpoints}

| Method and path | Purpose |
| --- | --- |
| `GET /api/health` | Mode, critical tasks, readiness and recording health |
| `GET /api/state` | Current arena, robot, camera and event snapshot |
| `GET /api/config` | Persistent configuration |
| `PUT /api/config` | Validate/save; all robots must be disarmed |
| `POST /api/robots/{id}/arm` | `{"enabled":true}` arms; `false` disarms |
| `POST /api/robots/{id}/release` | Stop/disarm if control ID still matches; returns `released` |
| `POST /api/robots/{id}/command` | Individual velocity |
| `POST /api/commands` | Jointly validate a velocity batch |
| `POST /api/stop` | Stop and lock the entire fleet |
| `POST /api/reset-stop` | Release global stop without arming |
| `GET /api/camera/stream` | Proxy the configured MJPEG vision stream |
| `WS /ws` | Latest state about every 100 ms, with no historical backlog |

## Action format and limits {#action-format-and-limits}

```json
{
  "car-01": {"v": 0.05, "omega": 0.0, "ttl_ms": 300},
  "car-02": {"v": 0.05, "omega": 0.0, "ttl_ms": 300}
}
```

This is the `/api/commands` format. Individual endpoints accept the inner velocity object. Schema limits are −1 to 1 for `v` and −6 to 6 for `omega`. Actual commands use the lower of configuration and device limits; schema maxima are not recommended physical speeds. TTL is 100–500 ms.

Arming and nonzero actions require `X-Control-ID` matching the arming request. Zero velocities can stop motion but do not release disarming or global-stop conditions.

`release` also requires `X-Control-ID`. Ownership checking and stopping are atomic on the server. A mismatch or already released robot returns `{"released":false}` without affecting a new owner. Use this for cleanup. Explicit `arm` with `enabled=false` and global stop may still stop other controllers' robots. Python callers should use a managed [SDK](../guide/python-sdk) session.

## Responses and state {#responses-and-state}

Invalid input returns 422; missing robots return 404. Ownership, localization, protection or arming conflicts normally return 409. Failed joint validation sends no partial new motion from that batch and locks participating robots owned by the requesting controller.

`armed` becomes true only after device confirmation. ACK establishes protocol state; physical motion needs wheel-speed and vision measurements.

`ready` concerns all configured robots, not only an experiment subset. The server accepts 1–16 robot configurations and provides four reference firmware environments. Larger scales need separate validation.

## State data {#state-data}

Pose is `x/y/theta`; identity is `robots[].config.id`. Inspect online, localization, arming, faults, command acknowledgment, wheel speed, voltage and stop reasons too. Unknown measurements are `null`, not zero.

HTTP and WebSocket expose latest snapshots without guaranteeing every historical state is observed. Use logs for run evidence and add experiment-layer observation/action associations.
