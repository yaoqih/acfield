# Troubleshooting

Inspect `/api/health`, events in `/api/state` and device serial output before changing settings. A stop reason is usually more informative than an unresponsive button.

| Symptom | First checks |
| --- | --- |
| Console opens but robot does not move | Global stop, explicit arming, matching control ID |
| Hardware cannot arm | Identity/binding, heartbeat, localization, firmware, latched faults |
| Stops immediately after arming | Pose jumps, spacing/boundary envelope, heartbeat/action expiry |
| Camera online but localization invalid | Actual frame age, occlusion, calibration, provenance and quality |
| Stops after a few hundred milliseconds | Renewal before TTL; blocked policy/server |
| Another page cannot control a robot | Exclusive ownership; disarm from the original controller or wait for expiry |
| Incomplete logs | Health dropped/error fields, disk and directory permissions |
| Firmware builds but motors do not run | motorsEnabled, counts per turn, faults, directions and wiring |

## Fault and warning codes {#fault-codes}

This table describes current firmware **0.2.3**. Distinguish the fields in `/api/state` first:

| Field | Meaning |
| --- | --- |
| Robot `warning` | Advisory only; does not stop, disarm or affect arming, ownership or motion |
| Robot `fault` | Latched device fault; stops and disarms immediately, accepting only stop commands. Fix the cause, restart the device, bind again and explicitly arm |
| Robot `stop_reason` | Current device state or latest stop reason; changing to `server_stop` does not mean `fault` has cleared |
| Robot `reason` | Server control state, waiting condition or protection reason, usually shown in Chinese |
| Top-level `system_fault` | Control/vision background task failure, containing the task name and exception type; stops all robots. Fix the cause and restart the server |

| Code | Level | Trigger with default configuration | Checks and recovery |
| --- | --- | --- | --- |
| `battery_sensor` | `warning` | INA219 read failure, conversion not ready or voltage outside 7–16 V; voltage becomes unknown | Check power, I2C wiring and address `0x42`; the next valid reading clears it without a restart. Invalid readings interrupt the undervoltage timer |
| `battery_low` | `fault` | Valid voltage continuously below 10.5 V for 1 s | Measure the battery and voltage drop under load; recharge or replace it. Voltage recovery does not clear a latched fault; restart the device |
| `motors_disabled` | `fault` | Compiled with `motorsEnabled=false` | After calibration, set it to `true`, rebuild and flash; console arming alone cannot enable it |
| `encoder_calibration_required` | `fault` | Either `pulsesPerTurn` value is not positive | Measure single-channel RISING counts per output-shaft turn, update the configuration, rebuild and flash |
| `control_overrun` | `fault` | Invalid, zero or over-100 ms control interval | Check blocked tasks, mutex waits and control task load; fix the cause and restart the device |
| `encoder_no_response_left` | `fault` | Nonzero left-wheel target, no pulses for at least 800 ms and accumulated target travel of at least 3 pulse distances | Check left-wheel obstruction, wiring, encoder power and counts per turn; fix and restart the device |
| `encoder_no_response_right` | `fault` | Same no-response conditions on the right wheel | Check right-wheel obstruction, wiring, encoder power and counts per turn; fix and restart the device |
| `encoder_direction` | `fault` | Feedback opposes the target for about 200 ms, with absolute feedback above 0.01 m/s and target × feedback below −0.0001 | Lift the wheels and check `motorSign`, `encoderSign` and wiring. This code has no side suffix; inspect both wheels in serial output, fix and restart |

Version differences: firmware **0.2.1** latched `battery_sensor` as a fault. If the console still shows it as a device fault, update both server and firmware and restart the device; refreshing the page or releasing global stop cannot clear that old latch. **0.2.3 removed `wheel_overspeed`**; older firmware used that fault when measured wheel speed exceeded three times the firmware wheel-speed limit. Current firmware still limits target wheel speed. Older servers may reject telemetry containing the new `warning` field, even when `null`, so update both ends together.

## Stops, waiting conditions and recovery {#control-states}

These are states or control conditions rather than latched device faults. Resolve any `fault` or `system_fault` first, then follow the relevant recovery steps.

| Message or `stop_reason` | Meaning and recovery |
| --- | --- |
| `boot`, `server_stop` / waiting for stop binding | Startup or a stop command; wait for stop acknowledgment, then explicitly arm. If an online device never confirms binding, check identity, server address and versions; 0.2.2 fixed command rejection caused by parsing the same mutable JSON buffer twice |
| `link_lost` / device reconnect | Wi-Fi state changed or the server detected reconnection; restore communication, complete stop binding and arm again. Motion never resumes automatically |
| `command_timeout` / command expired | A nonzero motion command was not renewed before TTL (100–500 ms allowed); restore renewal and arm again. Duplicate sequence numbers do not renew TTL |
| `armed`, `idle`, `driving` | Normal states: armed, zero velocity while remaining armed, and moving |
| Device offline | No valid telemetry for more than 1 s; check power, Wi-Fi, firmware server IP, UDP ports and protocol compatibility |
| Pose expired / localization unavailable | When localization is required, pose age exceeded 200 ms; check tags, camera and calibration, then arm again after recovery |
| Waiting for device time sync / browser-server time sync | Check device-server UDP and browser-server WebSocket separately; both clocks must be ready for console motion |
| Arena boundary / inter-robot distance / another robot's pose unavailable | Check poses, body envelopes and predicted paths, then explicitly arm when conditions permit. `ROBOT_ALLOW_UNLOCALIZED_CONTROL=1` skips localization, boundary and spacing checks |
| Global stop latched | Release global stop, then arm each robot; release does not clear device faults or resume motion |
| Another page owns control / ownership expired | Ownership is exclusive; disarm or release from the original controller. No renewal for 10 s stops the robot, requiring arming again |
| Vision configuration updating / synchronization failed | Wait for completion or fix the vision connection and configuration, then arm again |

Serial `[status]` includes `fault`, `warning`, both wheels' target/measured speeds, PWM and encoder counts. Record these values together with firmware version and events when reporting a problem.

## Missing frontend {#missing-frontend}

`./run.sh` installs/builds if artifacts are missing. Check Node and dependency installation on failure. Run `npm --prefix frontend ci` and `npm --prefix frontend run build` manually inside `robot_server/`. Rebuild after changing source when an older artifact already exists.

## Skipped contract tests {#skipped-contract-tests}

Backend tests need a host C++ compiler and PlatformIO-installed ArduinoJson:

```bash
python3 -m pip install platformio==6.1.18
pio pkg install -d esp32_software/firmware -e general-driver
```

Missing local dependencies cause explicit skips. CI sets `ACFIELD_REQUIRE_FIRMWARE_CONTRACT=1` so missing dependencies fail instead of producing a misleading green result.

## Ports already in use {#ports-already-in-use}

Defaults are HTTP 8000, device UDP 9999 and vision HTTP 8765. Check old processes. Do not add server workers to resolve contention. Ports may change, but update server, firmware and examples consistently.

## Native detector crashes on Linux cleanup {#native-detector-crashes-on-linux-cleanup}

The upstream cleanup order in pupil-apriltags 1.0.4.post11 can crash Linux when releasing a detector; see the [upstream discussion](https://github.com/pupil-labs/apriltags/pull/76). `native_apriltag.py` destroys the detector before its tag families. The dependency is pinned and subprocess tests repeat detection/destruction. Review the compatibility layer when updating native dependencies.

## Report a useful issue {#report-a-useful-issue}

Include platform revision, mode, OS, firmware/hardware versions, minimal steps, relevant events and stop reasons. Separate measurements from guesses. Remove credentials/private data and use the [Bug Report template](https://github.com/yaoqih/acfield/issues/new/choose).
