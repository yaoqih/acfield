# Architecture

One computer manages shared infrastructure while each robot runs a local control loop. The Python velocity example submits at approximately 10 Hz; console joystick and server loops run at 40 Hz, firmware motion tasks at 100 Hz and telemetry at 40 Hz. These are implementation settings; end-to-end performance requires measurement.

## Data and control paths {#data-and-control-paths}

```text
Fixed camera
    │ Images
    ▼
apriltag_live.py ── World pose, provenance, frame age ──┐
                                                       ▼
Policy ── HTTP joint velocities ──► robot_server ◄── Web console
                                      │    │
                             JSONL ◄──┘    │ Wi-Fi / UDP
                                           ▼
                                     ESP32 / Robot
                              TTL, wheel control, faults
                                           │
                                     Encoder motors
                                           └─ Telemetry to server
```

## Module responsibilities {#module-responsibilities}

| Module | Responsibility | Work kept explicit elsewhere |
| --- | --- | --- |
| Localization | Detection, intrinsic/extrinsic calibration, tag-height correction, source and age | Policy planning, device identity |
| Control server | State, ownership, joint validation, protection, transport, recording | Training and research tasks |
| Python SDK | Typed HTTP, explicit commands, control sessions and conditional release | Background renewal, policies, tasks |
| Policy script | Observation-to-action mapping and algorithm state | Bypassing arming or expiry |
| Firmware | Packet validation, wheel-speed execution, TTL and device faults | Global localization or path planning |
| Web console | Manual operation, configuration and diagnosis | Replacing server-side expiry |

## One owner of state {#one-owner-of-state}

A single FastAPI process owns robot, ownership and command state. SQLite stores configuration, trails live in bounded memory, and JSONL is written through a bounded queue. The same server hosts the frontend without runtime CDN dependencies.

Use one worker. Additional workers duplicate state and contend for the UDP port; they do not directly scale the controller. Run CPU-heavy policies in external processes and submit results with explicit lifetimes.

## Atomicity of joint actions {#atomicity-of-joint-actions}

`POST /api/commands` validates the shared set of candidate velocities before sending new motion. Failure prevents partial dispatch of that batch and disarms involved robots owned by the requesting source.

This boundary belongs to server validation. UDP delivery, device scheduling and motor startup retain timing skew. The platform provides clock synchronization and scheduled execution. A joint request still does not establish physical synchronization; measure clock error, device scheduling and mechanical response. See [device timing](../reference/protocol#clock-synchronization-and-scheduling).

## Coordinates and control point {#coordinates-and-control-point}

World distances are metres; angles are radians, counterclockwise positive. Body x points forward and y left. The differential-drive control point is the drive-axle midpoint. Tag offsets describe the body-frame vector from this point to the tag centre:

```text
body_heading = visual_world_heading + heading_offset
control_point = tag_centre − R(body_heading) × tag_offset
```

The tag-board centre differs from the axle midpoint: a centred tag on the compact acrylic candidate is nominally 30.5 mm forward of the axle, compared with approximately 16 mm for V11. Check heading and offsets after assembly. Body-envelope offsets and tag offsets are separate parameters; changing tag size does not update either offset.

## Engineering modules and repositories {#engineering-modules-and-repositories}

Established paths remain: `robot_server/`, `esp32_software/firmware/`, root vision scripts and `web/`. Stable paths preserve cross-component tests. Package structure can improve without changing external interfaces or immediately splitting repositories.

`sdk/python/` builds and installs independently as `acfield` without importing backend implementation. Server, SDK and docs are reviewed together. Algorithms can install the SDK in another environment or computer and connect through HTTP. See the [Python SDK](../guide/python-sdk).
