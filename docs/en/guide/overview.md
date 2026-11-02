# Overview

ACField is an open multi-robot testbed maintained by AClab, the Algorithms and Collaboration Lab. Its reference setup uses four indoor differential-drive robots, a fixed camera and a control computer. It provides the path from localization to velocity execution so researchers can connect their own control and collaboration algorithms.

## Platform responsibilities {#platform-responsibilities}

The platform aggregates poses and device state, accepts individual or joint velocity commands, manages ownership, explicit arming, command lifetimes and fault stops, and records runtime events. The web console supports debugging; the HTTP interface connects algorithms.

Paper-specific policies, training, task definitions and statistical analysis can live in separate experiment repositories pinned to an ACField revision. Infrastructure can improve while published experiments retain a clear software reference.

## Choose a starting point {#choose-a-starting-point}

| Goal | Path | Equipment |
| --- | --- | --- |
| Understand the system and debug the API | [Hardware-free quick start](./quickstart) | Computer |
| Connect a controller | [Controller integration](./control) | Begin in demo mode |
| Test vision and calibration | [Localization](./localization) | Synthetic demo or camera |
| Build reference robots | [Hardware](../hardware/overview) → [Bring-up](../hardware/bringup) | Controller, motors, mechanical parts |
| Design a research experiment | [Research validity](../design/research) → [Recording](./recording) | Determined by the task |

## Current components {#current-components}

```text
Camera → AprilTag service → Control server → Wi-Fi / UDP → ESP32 → Encoder motors
                                ↑                          │
                        Web console / Policy               └─ Telemetry
```

Demo mode obtains state from a simplified motion model in the server; no camera, device or cloud service is needed. The vision module has its own synthetic-image demo. These are independent debugging tools and are not automatically coupled.

## Before you begin {#before-you-begin}

This is a development preview. Four robots define the reference scale. A configuration accepting more robots does not establish measured performance at larger scales. The reference hardware still needs first-article testing; [capabilities and evidence](./status) separates software checks from physical performance.
