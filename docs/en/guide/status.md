# Capabilities and evidence

**Current stage: development preview.** This page separates implemented features, software checks and physical measurements. It describes scope, not hardware certification or a performance report.

## Available capabilities {#available-capabilities}

| Module | Implementation | Current boundary |
| --- | --- | --- |
| Console | Manual control, arena and trails, device configuration, global stop | Local computer or trusted experiment LAN; no account system |
| Server | Joint velocity validation, ownership, state streaming, velocity limits | Single process; not hard real time |
| Python SDK | Independent installation, typed state, joint actions, confirmed arming and conditional release | Synchronous HTTP; 0.1.0 preview; no async/WS client |
| Vision | AprilTags, world calibration, provenance and freshness checks | External intrinsic calibration; arena-wide accuracy and latency need measurement |
| Firmware | Wheel-speed control, explicit arming, TTL, encoder and undervoltage faults | Per-robot calibration required; motor output disabled by default |
| Protection | Stops for stale localization, link failure, boundaries and spacing | Conservative models; measured stopping distances still needed |
| Recording | Configuration, poses, actions, telemetry and stop reasons in JSONL | No complete episode evaluation or replay system |
| Reference hardware | Two-part V11 chassis, parameterized sources, nominal geometry checks | First-article assembly and physical acceptance pending |

## Recheck the software evidence {#recheck-the-software-evidence}

GitHub Actions builds the console and four firmware environments, and runs control, vision and actual-firmware parser contract tests. Green CI means that revision passed its software checks. Counts and outcomes for each revision are recorded in [Actions](https://github.com/yaoqih/acfield/actions).

Before import, the source project recorded 33 backend tests, 10 vision tests and four firmware builds passing. That history is not evidence for future revisions.

The V11 geometry report records two valid STL files and 213 nominal assembly checks, including the cover’s continuous upper tag face and orientation. These use supplier dimensions and estimated mass; they do not test strength, print tolerances, tire friction or motor dynamics.

## Physical evidence still needed {#physical-evidence-still-needed}

Measure first-article dimensions and contact, encoder counts per turn, direction, effective wheel diameter/track, wheel-speed tracking, arena-wide position/heading error and data age, wireless delay/loss, and stopping time/distance at different speeds. Current public material does not establish that four physical robots passed these checks.

## Planned research layer {#planned-research-layer}

The first SDK is available; stability needs use across experiments. Fixed-step simulation, standard tasks, episodes, constrained observations/communication, evaluation and replay remain on the [roadmap](../community/roadmap). The current demo supports interface debugging, not physical-performance ranking.
