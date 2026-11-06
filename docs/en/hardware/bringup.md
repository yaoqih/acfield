# Firmware and bring-up

Measure one complete control loop before replicating robots. Firmware currently allows motor output (`motorsEnabled=true`), but encoder counts per turn, direction, PI gains and useful limits are still uncalibrated; the first power-up must be with the wheels lifted, not on the floor.

The current validation sample uses two A12, 12 V, 1:100, three-wire encoder motors. The CAD candidate and some dynamics notes use 1:20, whose nominal speed is much higher; re-enter the measured ratio, counts and limits during bring-up.

## Configure and build {#configure-and-build}

Install PlatformIO, then run from the root:

```bash
python3 -m pip install platformio==6.1.18
cp esp32_software/firmware/include/secrets.example.h esp32_software/firmware/include/secrets.h
# Set Wi-Fi and server IPv4 in secrets.h; Git ignores this file
pio run -d esp32_software/firmware -e general-driver
```

`general-driver` targets car-01; the remaining environments are `car-02`, `car-03` and `car-04`. Select the intended environment when flashing:

```bash
pio run -d esp32_software/firmware -e car-02 -t upload
pio device monitor -d esp32_software/firmware -e car-02
```

## Staged acceptance {#staged-acceptance}

| Stage | Actions and evidence | Before advancing |
| --- | --- | --- |
| Power off | Polarity, insulation, fuse, fasteners, ground contact, caster/harness clearance | Components and wiring match; no scraping or loose parts |
| Output disabled | Turn wheels manually and record multiple revolutions; cross-check voltage | Enter measured counts and resolve VCC/GND diagram conflicts |
| Wheels lifted, low speed | Motor/encoder directions, forward/left turn, initial PI | Correct feedback sign and no persistent divergence |
| One robot on floor | Minimum stable speed, straight/spot turns, stopping time/distance | Controllable on the actual surface; protection assumptions match measurements |
| Camera integration | Arena-wide pose/heading error, age, occlusion, camera movement | Invalid data expires; recovery does not rearm |
| Fault injection | Network/server loss, encoder anomaly, undervoltage, reboot | Correct stop/disarm behavior and visible fault reasons |
| Two to four robots | Identity, ownership, joint actions, spacing protection, continuous runs | Save evidence before automatic policies |

Measure encoder counts using the firmware's single-channel rising-edge method, rather than copying a vendor's quadrature ×4 value. Calibrate wheels separately.

## Important hardware boundaries {#important-hardware-boundaries}

Reference pins, voltage thresholds and diagnostics are in the [firmware README](https://github.com/yaoqih/acfield/blob/main/esp32_software/firmware/README.md). Verify motor/encoder pin numbers and measurements; do not rely only on wire colours.

The initial 3S undervoltage setting latches a stop below 10.5 V for one second. Pack voltage does not replace per-cell monitoring. Include a physical power switch and power protection. Verify full-charge supply behavior, temperatures and battery retention on the first robot.

## Keep a minimal measurement record {#keep-a-minimal-measurement-record}

For each robot, preserve component revisions, wheel diameter/track, counts per turn, directions, PI gains/limits, localization offsets and stopping conditions/results. Record the evidence behind each threshold adjustment. Hardware revisions and parameters should be traceable to runtime logs.
