# State Data Dictionary

Algorithms read `GET /api/state`. WebSocket snapshots use the same fields and add `server_time_ms`.

**Check validity before using numbers.** Expired localization retains the last `x/y/theta`. Wait for fresh localization when `visible=false`. Encoder and wheel feedback become `null` when the device goes offline.

Voltage, battery, firmware and device status may retain their last values. Check `online` and `heartbeat_age_ms` when using them.

## Snapshot and health {#snapshot-and-health}

| Field | Meaning and use |
| --- | --- |
| `mode` | `demo` uses the server simulator; `hardware` uses the device transport |
| `session` | Server control session. Mode switches, configuration saves and restarts change it. Read configuration and establish control again after a change |
| `timestamp` | Server-mapped Unix seconds at snapshot construction |
| `estop` / `system_fault` | Global stop / background-task fault. No fault is `null` |
| `allow_unlocalized_control` | Whether localization and position checks are bypassed. Policies still check observation validity |
| `arena.width/height` | World X/Y bounds in metres, starting at `(0,0)` |
| `clock` | Server time source, NTP state and pending correction; inspect `GET /api/time` |
| `camera` | `connected` means a usable calibrated live frame; `available` means a recent camera frame; `fps` is reported rate and `reason` explains status. Some waiting states omit `available` |
| `events` | Bounded recent list with `time` in Unix seconds and `message`. Use JSONL for full recording |
| `robots` | Look up by `config.id`; list order does not define identity |

`GET /api/health` reports `status=ok` or `degraded`, with HTTP 200 or 503 respectively. `ready` covers all configured robots under current server conditions. `run_id` locates logs; `recording_dropped/error` report recording completeness. UDP counters are in the [API reference](./api#endpoints).

`clock` contains `source` (`local` / `ntp`), `ntp_at` (Unix seconds of the latest successful NTP probe), `ntp_error` (latest error or `null`), and `pending_correction_ms` (remaining gradual clock correction). Camera `connected` requires a calibrated frame under 200 ms old. `available` accepts a live-camera frame under 1 s old. Check each robot's `visible` separately.

## Robot fields {#robot-fields}

| Field | Source, units and validity |
| --- | --- |
| `config` | Saved identity, dimensions, offsets and limits; see [coordinates and configuration](./coordinates) |
| `online` / `heartbeat_age_ms` | Whether telemetry is within its deadline / milliseconds since last telemetry; age is `null` before any telemetry |
| `visible` / `pose_age_ms` | Whether localization is fresh / pose age in milliseconds; age is `null` when absent or explicitly invalidated |
| `x/y/theta` | Axle-midpoint world pose in metres / metres / radians, counterclockwise positive. Old values may remain when `visible=false` |
| `bound` / `armed` / `arm_pending` | Stop binding complete / arming confirmed / awaiting arm confirmation |
| `control_owner` | Current control ID; `null` when free |
| `target_v/target_omega` | Current server target in m/s and rad/s after server clamping. Diagnostic `target_v` uses the PWM transport mapping |
| `effective_max_v` / `effective_max_omega` | Effective target limits from device reports and saved configuration |
| `measured_v` / `measured_omega` | Device encoder-based linear/angular speed in m/s and rad/s, available when online and reported. Demo provides simulated feedback |
| `wheel_left` / `wheel_right` | Device-estimated wheel ground speeds, m/s, forward positive. Offline or absent values are `null` |
| `encoder_left` / `encoder_right` | Raw cumulative counts before `encoderSign`, reset on device reboot, `null` offline or absent |
| `estimated_v` | Server longitudinal velocity from consecutive poses, smoothed, m/s; needs at least two adjacent valid poses |
| `acceleration` | Difference of the smoothed vision velocity, m/s²; `null` with invalid localization or insufficient samples |
| `imu` | Sensor sample described below; `null` offline, on older firmware or when unavailable |
| `voltage_v` / `battery` | Voltage in V / estimated charge in %; unknown is `null`. Demo charge is a display value |
| `firmware` / `device_state` | Firmware version / `unbound`, `disarmed`, `armed`, `fault`; may be `null` in demo |
| `seq` / `ack_seq` | Latest server command sequence / device acknowledgment; initial `ack_seq=-1` |
| `command_status` | `idle` initially, `sent` after sending, `confirmed` after acknowledgment, `expired` after expiry |
| `applied_seq` | Latest control update processed by the device. Inspect separately from `ack_seq`; absent is `null` |
| `sampled_at_ms` | Server-mapped Unix milliseconds at telemetry construction; check synchronization first |
| `clock_synced` / `clock_uncertainty_ms` | Whether the device accepts scheduled motion / estimated clock uncertainty in milliseconds; unknown uncertainty is `null` |
| `fault` / `warning` | Latched fault / advisory warning; `null` when absent. See [fault codes](../guide/troubleshooting#fault-codes) |
| `reason` | Current server control or waiting explanation |
| `stop_reason` / `last_stop_reason` | Device stop explanation / retained latest server stop reason; absent is `null` |
| `motion_echo_rejections` | Boot-lifetime device rejection count for expired/unknown telemetry echoes; `null` on older firmware |
| `encoder_diagnostic` | `max_pwm` and `pwm_per_mps` for recognized diagnostic firmware, otherwise `null` |
| `diagnostic_running` / `diagnostic_remaining_ms` | Server renewal active / remaining milliseconds. The latter is `null` when inactive |
| `corners` / `trail` | Four body corners / bounded historical XY points in world metres. May contain old positions; check `visible` |

### IMU {#imu-fields}

| Field | Meaning |
| --- | --- |
| `sampled_mono_us` | Device monotonic microseconds when reading completed; requires a mapping to compare with server time |
| `sensor_ticks` | Raw 24-bit sensor timestamp, subject to wraparound |
| `age_ms` | Sample age when the device sent telemetry, excluding subsequent network wait |
| `saturated` | Whether the sample reached a sensor range limit |
| `accel_m_s2` | Chip XYZ acceleration in m/s², including gravity |
| `gyro_rad_s` | Chip XYZ angular velocity in rad/s, including bias |

IMU axes use the chip frame. Calibrate mounting orientation and bias before body-motion analysis. `acceleration` uses vision differences, with separate sampling, coordinates and filtering.

## Fresh and stale {#fresh-and-stale}

These are robot-field excerpts. Download full [fresh](/examples/state-fresh.json) and [stale](/examples/state-stale.json) examples produced by the state serializer for interface reference.

```json
{"online": true, "visible": true, "x": 0.84, "y": 0.84, "theta": 0.0, "pose_age_ms": 25, "measured_v": 0.05}
```

```json
{"online": false, "visible": false, "x": 0.84, "y": 0.84, "theta": 0.0, "pose_age_ms": 4000, "measured_v": null}
```

<!-- docs-test: state-reader -->
```python
from acfield import Client

with Client("http://127.0.0.1:8000") as client:
    robot = client.state().robot("car-01")
    if robot.online and robot.visible and robot.pose_age_ms is not None:
        print(robot.x, robot.y, robot.theta, robot.pose_age_ms)
    else:
        print("Waiting for fresh state")
```

## Time bases {#time-bases}

| Time | Use |
| --- | --- |
| `timestamp`, log `time` | Server-mapped Unix seconds, usable for selecting an experiment interval |
| `server_time_ms`, `sampled_at_ms` | Server-mapped Unix milliseconds; device values need synchronization and uncertainty checks |
| Log `monotonic`, pose event `at` | Server monotonic seconds, suitable for intervals |
| IMU `sampled_mono_us` | Device monotonic microseconds, directly comparable only within the same device boot |

HTTP response time also includes network wait. Define clock references, uncertainty and pairing when measuring sample-to-execution latency. See [protocol timing](./protocol#clock-synchronization-and-scheduling).
