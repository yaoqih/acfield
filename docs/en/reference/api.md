# HTTP and WebSocket

The control service normally uses `http://127.0.0.1:8000`, with runtime OpenAPI at `/docs`. Vision normally uses `http://127.0.0.1:8765` and has separate endpoints. The two `/api/state` responses differ.

## Control endpoints {#endpoints}

| Method and path | Purpose |
| --- | --- |
| `GET /api/health` | Mode, critical tasks, readiness and recording health |
| `GET /api/state` | Arena, robot, camera and event snapshot |
| `GET /api/time` | `server_time_ms`, clock source, NTP state and pending correction |
| `GET /api/config` | Persistent configuration |
| `PUT /api/config` | Validate/save; all robots must be disarmed |
| `PUT /api/mode` | `{"mode":"demo"}` or `hardware`; keep global stop active after switching |
| `GET /api/vision/config?url=...` | Read vision status and camera profile |
| `POST /api/vision/cameras` | Scan camera IDs 0–5 on the vision host |
| `POST /api/vision/operations` | `calibrate`, `load_world` or `reset_world`; robots remain locked |
| `POST /api/robots/{id}/arm` | `{"enabled":true}` arms; `false` disarms |
| `POST /api/robots/{id}/release` | Stop/disarm if control ID still matches; returns `released` |
| `POST /api/robots/{id}/command` | Individual velocity |
| `POST /api/commands` | Jointly validate a velocity batch |
| `POST /api/stop` | Stop and lock the fleet |
| `POST /api/reset-stop` | Release global stop without arming |
| `GET /api/camera/stream` | Proxy configured vision MJPEG |
| `WS /ws` | Latest state about every 25 ms, time sync and ordered single-robot control |

## Action format and limits {#action-format-and-limits}

```json
{
  "car-01": {"v": 0.05, "omega": 0.0, "ttl_ms": 300},
  "car-02": {"v": 0.05, "omega": 0.0, "ttl_ms": 300}
}
```

This is the `/api/commands` format. Individual endpoints take the inner object. `v` uses m/s with schema range −1 to 1; `omega` uses rad/s with range −6 to 6. Actual limits are the lower of configuration and device reports. TTL is 100–500 ms. Schema maxima are not recommended physical speeds.

A velocity object may include `execute_at_ms` in server-mapped Unix milliseconds. For nonzero motion, explicit execution time must be 15–150 ms ahead of the server clock; hardware also requires a synchronized device. When omitted, synchronized devices get a default 60 ms lead; unsynchronized devices use immediate compatibility mode. Zero motion bypasses scheduling and clears future motion. See [device timing](./protocol#clock-synchronization-and-scheduling).

Use the same `X-Control-ID` for HTTP arming and nonzero actions. Zero motion can stop but cannot release disarming or global stop. `release` also requires the ID and atomically checks ownership before stopping/disarming. A mismatch or prior release returns `{"released":false}` without affecting a new owner. Explicit disarm and global stop can stop other controllers. Python callers should use managed [SDK](../guide/python-sdk) sessions.

## WebSocket messages {#websocket-messages}

After connecting to `/ws`, receive latest snapshots similar to `/api/state` with extra `server_time_ms`. Snapshots have no message `type`; distinguish them from control receipts. Send `{"type":"time_sync","t1":CLIENT_SAMPLE_TIME}` to receive echoed `t1`, server receive `t2` and send `t3`, in milliseconds. Sample client receive time `t4` to form the four-timestamp exchange.

Arm through HTTP first, then send single-robot control:

```json
{
  "type": "control",
  "seq": 1,
  "robot_id": "car-01",
  "owner": "my-controller",
  "command": {"v": 0.05, "omega": 0.0, "ttl_ms": 300}
}
```

`seq` is a strictly increasing integer per connection. `owner` has 1–64 characters, stays fixed for the connection and matches the HTTP arming ID. Success returns `{"type":"control_ack","seq":1,"packet":{...}}`. A business rejection returns `control_error`, the original `seq` and `message`. Invalid sequences/owners close the connection. Disconnect conditionally releases that owner's robots.

`control_ack` establishes server acceptance, not device ACK. The console sends the latest joystick target every 25 ms and skips missed cycles. Hardware waits for browser/device synchronization, then schedules at sample time +100 ms. Disconnect or congestion triggers an HTTP fallback stop/disarm and requires arming again after recovery.

## Responses and state {#responses-and-state}

Invalid HTTP input returns 422, missing robots 404, and ownership, localization, protection or arming conflicts normally 409. Failed joint validation sends no partial new motion from that batch and locks involved robots owned by the requester.

Hardware `armed` requires device confirmation. `ack_seq` means protocol acceptance; `applied_seq` means a device control update was processed. Neither proves physical motion; inspect wheel speeds, encoders and vision.

`ready` concerns all configured robots. The server accepts 1–16 configurations and provides four reference firmware environments. `allow_unlocalized_control=true` skips pose freshness, boundary and spacing protection; binding, heartbeat, faults, arming and TTL still apply. See [configuration](../guide/configuration) for startup defaults.

Hardware `PUT /api/config` may include a `vision` profile. The server locks robots, applies vision settings, then saves control settings only after success. Failure keeps global stop active.

## State data {#state-data}

Identity is `robots[].config.id`; pose is `x/y/theta`. Inspect online, localization, arming, faults, command acknowledgment, wheel speed, voltage and stop reasons. Unknown `null` values are not zero. Per-robot fields include `clock_synced`, `clock_uncertainty_ms`, `sampled_at_ms` and `applied_seq`. Snapshot `timestamp` uses seconds; WebSocket `server_time_ms` and telemetry sample times use milliseconds.

HTTP and WebSocket provide latest snapshots without complete historical delivery. The page's server-update age measures monotonic time since this page received a snapshot; it is not telemetry age or end-to-end latency. Use logs with experiment-owned observation/action associations.

## Independent vision endpoints {#vision-service-endpoints}

These belong to vision (normally port 8765), not the control server:

| Method and path | Purpose |
| --- | --- |
| `GET /api/state`, `GET /api/config` | Detection snapshot; configuration and state |
| `POST /api/config` | Validate, apply and save a complete camera profile; wait for worker confirmation |
| `POST /api/cameras` | Scan cameras on the vision host |
| `POST /api/operations` | `{"action":"calibrate"}`, `load_world` or `reset_world` |
| `POST /api/control` | Queue source, detector, recording or clear-tracks actions; 202 means queued only |
| `GET/POST /api/preview` | `{"width":0,"fps":30}`; display only, current process |
| `POST /api/calibration` | ChArUco `capture`, `solve`, `reset`; board fields in the [guide](../guide/localization#charuco-intrinsics) |
| `POST /api/calibration/apply` | Save current solved intrinsics or measured world coordinates; clear old extrinsics |
| `GET /stream.mjpg`, `GET /api/snapshot.jpg` | MJPEG and current screenshot |
| `GET /api/export.json`, `GET /api/export.csv` | Current state/tag export |
| `GET /calibration`, `GET /calibration/board.pdf` | Calibration page and default A4 board |

Vision has no `/api/health`. Writes enforce same-origin browser access. Disarm all robots before direct configuration changes and reload the profile in the control server afterwards.
