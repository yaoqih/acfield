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
