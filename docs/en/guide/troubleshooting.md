# Troubleshooting

Inspect `/api/health`, events in `/api/state` and device serial output before changing settings. A stop reason is usually more informative than an unresponsive button.

| Symptom | First checks |
| --- | --- |
| Console opens but robot does not move | Global stop, stop binding, matching control ID |
| Hardware cannot arm | Identity/binding, heartbeat, localization, firmware, latched faults |
| Stops immediately after arming | Pose jumps, spacing/boundary envelope, heartbeat/action expiry |
| Camera online but localization invalid | Actual frame age, occlusion, calibration, provenance and quality |
| Stops after a few hundred milliseconds | Renewal before TTL; blocked policy/server |
| Another page cannot control a robot | Exclusive ownership; disarm from the original controller or wait for expiry |
| Incomplete logs | Health dropped/error fields, disk and directory permissions |
| Firmware builds but motors do not run | motorsEnabled, counts per turn, faults, directions and wiring |

## Fault and warning codes {#fault-codes}

This table describes current normal firmware **0.2.8**, which defaults to open-loop drive. Distinguish the fields in `/api/state` first:

Normal firmware estimates speed from pulses and elapsed time across the latest five control cycles (about 50 ms). Motor output and speed estimates still update every 10 ms, joystick commands remain at 40 Hz (25 ms), and raw cumulative counts are unchanged. Flash from the repository root with `pio run -d esp32_software/firmware -e general-driver -t upload`; serial startup should show `Motor control: open_loop`.

Version 0.2.8 sets `motorClosedLoop=false`: encoder feedback is only displayed and recorded, with no effect on PWM. Each wheel's target is multiplied by `feedForward=350`; straight targets of 0.10, 0.20 and 0.50 produce approximately 35, 70 and 175 PWM. If either output exceeds 255, both are scaled together to preserve steering ratio. Protocol/UI targets retain m/s units, but actual open-loop speed varies with battery, load and motor differences. The normal target limit remains 0.89 m/s; new server robot configurations default to 0.50 m/s.

Earlier 0.2.6 logs recorded estimated feedback around 5.98 m/s against a forward target around 0.17 m/s. PI can then clamp positive output to zero and accelerate again as feedback drops, plausibly explaining repeated jerks. Disabling encoder fault stops alone did not bypass PI. Open-loop drive isolates this feedback path; if PWM stays steady but motion still jerks, inspect low-duty starting behavior, power, drivers and mechanical resistance.

`encoderGuardsEnabled=false` continues to disable direction and no-response fault stops. After feedback, geometry/count calibration and PI tuning, set `motorClosedLoop=true` to restore closed-loop regulation. Restoring these two fault guards also requires `encoderGuardsEnabled=true`; rebuild and flash after changing either flag. Flashing restarts the device and clears old latched faults.

| Field | Meaning |
| --- | --- |
| Robot `warning` | Advisory only; does not stop, disarm or affect arming, ownership or motion |
| Robot `fault` | Latched device fault; stops and disarms immediately, accepting only stop commands. Fix the cause, restart the device, bind again and use fresh input |
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
| `encoder_no_response_left` | Disabled by default | Only when both `motorClosedLoop=true` and `encoderGuardsEnabled=true`: nonzero left-wheel target, no raw pulses for at least 1500 ms and accumulated target travel of at least 6 pulse distances; any pulse resets the interval | On older firmware or with closed loop and guards enabled, check left-wheel obstruction, wiring, encoder power and counts per turn; fix and restart the device |
| `encoder_no_response_right` | Disabled by default | Only with closed loop and guards enabled: same no-response conditions on the right wheel | Check right-wheel obstruction, wiring, encoder power and counts per turn; restart to clear an old latch |
| `encoder_direction` | Disabled by default | Only with closed loop and guards enabled: smoothed feedback continuously opposes the target for at least 1000 ms, with absolute feedback above 0.05 m/s, target × feedback below −0.0001, and accumulated reverse feedback travel of at least 6 pulse distances | Lift the wheels and check `motorSign`, `encoderSign` and wiring; inspect both wheels in serial output and restart to clear an old latch |

Version differences: firmware **0.2.1** latched `battery_sensor` as a fault. If the console still shows it as a device fault, update both server and firmware and restart the device; refreshing the page or releasing global stop cannot clear that old latch. **0.2.3 removed `wheel_overspeed`**; older firmware used that fault when measured wheel speed exceeded three times the firmware wheel-speed limit. Current firmware still limits target wheel speed. Older servers may reject telemetry containing the new `warning` field, even when `null`, so update both ends together.

## Stops, waiting conditions and recovery {#control-states}

These are states or control conditions rather than latched device faults. Resolve any `fault` or `system_fault` first, then follow the relevant recovery steps.

| Message or `stop_reason` | Meaning and recovery |
| --- | --- |
| `boot`, `server_stop` / waiting for stop binding | Startup or a stop command; wait for stop acknowledgment, then use fresh input. If an online device never confirms binding, check identity, server address and versions; 0.2.2 fixed command rejection caused by parsing the same mutable JSON buffer twice |
| `link_lost` / device reconnect | Wi-Fi state changed or the server detected reconnection; restore communication, complete stop binding and use fresh input. Motion never resumes automatically |
| `command_timeout` / command expired | A nonzero motion command was not renewed before TTL (100–500 ms allowed); restore renewal and use fresh input. Duplicate sequence numbers do not renew TTL |
| `armed`, `idle`, `driving` | Normal states: armed, zero velocity while remaining armed, and moving |
| Device offline | No valid telemetry for more than 3 s; check power, Wi-Fi, firmware server IP, UDP ports and protocol compatibility |
| Pose expired / localization unavailable | When localization is required, pose age exceeded 200 ms; check tags, camera and calibration, then use fresh input after recovery |
| Time synchronization unavailable | Console control remains available; the server sends immediately when the device clock is not synchronized. Check device-server UDP and browser-server WebSocket separately; incoming telemetry only confirms the device-to-server direction |
| Arena boundary / inter-robot distance / another robot's pose unavailable | Check poses, body envelopes and predicted paths, then use fresh input when conditions permit. `ROBOT_ALLOW_UNLOCALIZED_CONTROL=1` skips localization, boundary and spacing checks |
| Global stop latched | Release global stop, then use fresh input for each robot; release does not clear device faults or resume motion |
| Another page owns control / ownership expired | Ownership is exclusive; disarm or release from the original controller. No renewal for 10 s stops the robot, allowing fresh input to start again |
| Vision configuration updating / synchronization failed | Wait for completion or fix the vision connection and configuration, then use fresh input |

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

Normal firmware 0.2.8 maps logical left/right to physical B/A channels for this chassis, for both motor output and encoder feedback. Positive yaw still turns left, with a faster right-wheel target. The console, mobile and encoder pages start control with fresh input and automatically perform the device arm handshake. Stop, release, disconnect and expiry discard pending input; reconnect never replays old motion. Both normal and diagnostic telemetry expire after 3 s. Joystick output remains 40 Hz.
