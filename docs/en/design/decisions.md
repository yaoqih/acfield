# Design decisions

These decisions record the current choice, its costs and the evidence that could change it. They are not a permanent technical roadmap.

## D01 · One repository for the complete platform {#d01-one-repository-for-the-complete-platform}

**Choice:** Keep the console, server, localization, firmware, reference hardware and docs together. Paper-specific algorithms and training remain separate and pin a platform revision.

**Reason:** The device protocol needs cross-component integration, and contract tests compile the actual firmware parser. A single commit can update both endpoints; users obtain matching source versions in one place.

**Cost and reconsideration:** Multiple toolchains increase CI cost. Consider extraction when a module has independent users, maintainers and release cadence, after defining compatibility and continued integration testing.

## D02 · A fixed camera provides shared localization {#d02-a-fixed-camera-provides-shared-localization}

**Choice:** A camera and AprilTags establish world coordinates; robots do not run SLAM.

**Reason:** Shared coordinates are accessible for small, indoor, low-speed experiments and leave more research effort for collaborative decision making.

**Cost and reconsideration:** The camera is a common dependency. Occlusion, reflections and insufficient distant pixels limit the arena. Onboard perception, distributed localization or out-of-view operation need additional sources and explicit fusion/error models.

## D03 · HTTP for policies, UDP for devices {#d03-http-for-policies-udp-for-devices}

**Choice:** Policies use inspectable HTTP state/joint-action endpoints. The server exchanges compact JSON UDP packets with ESP32 devices.

**Reason:** Message volume is small at the reference scale, integration is approachable and many languages can call the API. Sessions, sequences, telemetry echoes and TTL address common reordering and stale commands.

**Cost and reconsideration:** HTTP is not hard real time; UDP has no delivery guarantee or authentication. Higher frequencies, precise synchronization, ROS integration or different networking requirements should motivate measured changes while keeping failure behavior testable.

## D04 · Devices check motion expiry independently {#d04-devices-check-motion-expiry-independently}

**Choice:** A 50 Hz device task checks TTL and controls wheel speed. Networking and I²C run in another task.

**Reason:** If the server, network or policy stops updating, each robot needs local logic to converge to a stop.

**Cost and reconsideration:** ESP32 scheduling, lock contention and physical response still need measurement. Software expiry does not establish physical stopping time. Measure task delays and motor dynamics before selecting a controller upgrade.

## D05 · Use the demo for integration; build simulation to need {#d05-use-the-demo-for-integration-build-simulation-to-need}

**Choice:** A lightweight kinematic demo first checks the console, interfaces and stop path.

**Reason:** Users without devices can inspect the system, and maintainers can diagnose most interface problems without a large simulator.

**Cost and reconsideration:** The model has no fixed-step research interface, rewards, complete tasks, friction or realistic link disturbances. Training and performance comparisons require independently validated simulation and protocols; the demo does not establish transfer performance.

## D06 · Make protective actions visible {#d06-make-protective-actions-visible}

**Choice:** Server protection checks boundaries, spacing, localization and device state, recording clamps and rejections.

**Reason:** Protection makes initial integration failures more manageable and provides evidence for interpreting experiments.

**Cost and reconsideration:** Protection changes policy behavior and may use global information unavailable to the policy. Report interventions. If interventions dominate operation, inspect spacing, models, error and policy adaptation before changing thresholds.
