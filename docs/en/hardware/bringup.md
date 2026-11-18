# Firmware and bring-up

Measure one complete control path before replicating robots. Normal firmware 0.2.9 allows motor output (`motorsEnabled=true`) and defaults to encoder wheel-speed regulation (`motorClosedLoop=true`) with initial `feedForward=250`, `kp=60` and `ki=0`. Both wheels currently use `88` encoder counts per turn. Verify counts, direction, PI gains and useful limits on each robot. Begin powered tests with the wheels lifted.

All four robots have changed from A12, 12 V, 1:100 motors to the same family at 1:20. With 34 mm wheels, the nominal 500 rpm rated point is about 0.89 m/s. Firmware limits are 0.89 m/s for linear and wheel speed and 6.00 rad/s for yaw. Server defaults are 0.50 m/s and 1.50 rad/s. Acceleration limiting has been removed. Current `wheelChannels={0,1}` maps logical left/right to physical A/B for both motors and encoders. Verify this mapping against each robot's wiring.

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

## Measure the parameters {#measurement-procedures}

Identify hardware with the [compatibility table](./compatibility). Repeat each measurement at least 3 times and retain raw readings, mean and maximum variation. These are **example acceptance targets** for low-speed bring-up. Set targets for your task before testing.

| Measurement | Procedure and calculation | Example target |
| --- | --- | --- |
| Output counts | Disable motion output, mark the tire, rotate 10 full turns and record each raw count change. `counts=abs(change)/10` | Within 1% over 3 repeats, positive forward feedback after `encoderSign` |
| Effective diameter | Push the loaded robot for 10 turns, measure distance L. `D=L/(10π)` | Within 1% over 3 repeats |
| Effective track | Pivot slowly through an independently measured turn θ, record wheel travel. `B=(s_right-s_left)/θ`, θ in radians | Within 5°/turn after updating and retesting |
| Straight speed | Run at 0.03, 0.05 and 0.10 m/s for 5 s with room to stop. Compare vision and encoder means over the middle 3 s | Target error and cross-sensor difference within 10%, without repeated starting/stopping |
| Tag offset | Measure forward/left offsets, hold axle midpoint fixed, rotate to 0°/90°/180°/270° | Corrected drift at most 10 mm |
| Stop time and distance | From steady 0.05 and 0.10 m/s, request stop and record video/logs until stationary | Record maxima over 3 repeats, inside the preallocated stopping distance |

Use single-channel rising-edge counts. Track estimation depends on calibrated wheel travel and is sensitive to slip. Repeat on the experiment floor. Verify the actual envelope and available arena before speed tests.

### Tune PI {#pi-tuning}

Verify counts, diameter, directions and wiring first. Keep `ki=0`. Record target/measured wheel speeds and PWM during low-speed steps. Adjust feed-forward toward the requested mean, then increase `kp` in small increments while comparing steady-state error and oscillation. Investigate counts and power when feedback jumps.

Change one parameter at a time. Repeat straight, turning and stop tests before choosing server limits. See [current defaults](../reference/defaults).

## Keep a minimal measurement record {#keep-a-minimal-measurement-record}

For each robot, preserve component revisions, wheel diameter/track, counts per turn, directions, PI gains/limits, localization offsets and stopping conditions/results. Record the evidence behind each threshold adjustment. Hardware revisions and parameters should be traceable to runtime logs.

These **illustrative filled values** explain the format. Replace them with measurements and attach raw logs.

| Item | Filled example | Your measurement |
| --- | --- | --- |
| Identity and versions | car-01, V11, 1:20, platform and firmware commits attached | Pending |
| Conditions | Flat PVC floor, battery 12.1 V, 3 repeats | Pending |
| Counts over 10 turns | Left 880/880/880, right 880/880/880 → 88/88 | Pending |
| Effective diameter / track | 0.0340 / 0.122 m, raw distances and angles attached | Pending |
| Tag and offset | Black frame 0.104 m, height 0.0646 m, measure forward offset | Pending |
| Straight target 0.05 m/s | Vision 0.048 m/s, encoder 0.050 m/s | Pending |
| Maximum low-speed stop | From 0.05 m/s, 0.18 s / 0.006 m | Pending |
| Arena localization | 9 points, 10 s each, position p95 8 mm, heading p95 2° | Pending |
| Decision and evidence | Passed chosen low-speed targets, logs and calibration attached | Pending |
