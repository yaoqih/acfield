# Case study of telemetry gaps and jerky motion

The 2026-11-12 investigation spans several historical builds. This page preserves evidence and reasoning. Use [Troubleshooting](./troubleshooting) for current procedures.

## Evidence {#evidence}

| Time and build | Observation | Supported interpretation |
| --- | --- | --- |
| 15:50:51, 15:51:00, 15:51:15 | Commands about every 25 ms, accepted telemetry gaps of 600–770 ms, stalled ACK, device `command_timeout` | A 200 ms motion echo deadline could reject continuously sent commands |
| 16:05–16:09 | 8 gaps of 1046–1129 ms, unchanged boot, no fault, `motion_echo_rejections=0` | The old 1 s server heartbeat triggered offline stops |
| 16:08:19.723–16:08:20.771 | Left count changed by 2483, about 4.22 m/s under the old calibration | Raw count changes conflicted with validation bounds |
| 16:09:13.122–16:09:14.177 | Left count changed by 33524, about 56.6 m/s | Investigate wiring/counts before interpreting estimated speed physically |
| New run after 16:10:53 | Gaps of 581/698 ms recovered to `armed/driving`, followed by the 120 s stop at 16:13:16 | Wider heartbeat and server renewal were active before speed-validation fixes |

Old validation rejected complete packets when wheel/linear speed exceeded ±3 m/s or yaw exceeded ±30 rad/s, discarding heartbeat, ACK and counts together. The maximum accepted wheel speed was exactly the quantized 2.848 m/s, consistent with validation losses. Historical logs lack per-packet rejection records, so additional network losses and the page event behind generic ownership-release messages cannot be reconstructed.

## Fixes and current checks {#fixes}

Diagnostic 0.2.4 widened the motion echo window to 1500 ms, retained 200 ms for binding/arming, and added `motion_echo_rejections`. Server heartbeats became 3 s for normal and diagnostic builds. Continuous diagnosis moved from a 30 s page timeout to a 120 s server deadline, retaining 500 ms motion TTL.

The server now retains finite raw speeds, rejects NaN/Infinity, and exposes `udp_received`, `udp_rejected`, `udp_rejections` and rejection events. The validation fix requires a server update. See [diagnostic procedures](./troubleshooting#encoder-diagnostics) for the current build and restoring normal firmware.

For new gaps, compare packet rejection counts, device echo rejection counts and ACK before inspecting Wi-Fi, power and wiring. Wider heartbeat tolerates short return-path gaps while motion expiry remains independent.

## Feedback and oscillation {#feedback-oscillation}

Firmware 0.2.6 recorded approximately 5.98 m/s left-wheel feedback against a 0.17 m/s target. PI could suppress forward output to zero, then raise it again as feedback dropped. Open-loop builds 0.2.7/0.2.8 isolated the feedback path. Current normal firmware uses closed-loop regulation again.

Record targets, raw counts, wheel speeds, PWM and loaded voltage together. Investigate counts for feedback jumps. With stable output and jerky motion, check starting duty, power, driver and mechanical resistance.
