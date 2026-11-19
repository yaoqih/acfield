# From one robot to intelligent collaboration

This task ladder connects platform setup, motion control, planning and intelligent algorithms. Each stage identifies deliverables, evidence of readiness and what the next stage can rely on.

The platform remains a [development preview](./status). These are proposed tasks and acceptance criteria. Actual completion depends on recorded evidence. Measure localization, speed and stopping distances during [bring-up](../hardware/bringup).

## Stage map {#stage-map}

| Stage | Question | Deliverable | Boundary for the next stage |
| --- | --- | --- | --- |
| 1 · Single-robot platform | Can one robot be observed, controlled and stopped consistently? | Calibrated robot, measurement record, logs | Fresh poses and time-limited velocity commands under recorded speed and arena conditions |
| 2 · Multi-robot platform | Can robots work independently at the same time? | Per-robot records and two-/four-robot integration report | Unique identities and traceable per-robot state, ownership and stop reasons |
| 3 · Reliable motion | Can a robot repeatedly reach a given goal? | Single-robot controller, baselines and error report | Goal and path tracking within declared initial conditions and speed limits |
| 4 · Multi-robot planning | Can robots complete constrained tasks in a shared arena? | Planner, tracker, conflict handling and evaluation | Feasible plans and execution for stated scenarios, with explainable failures and interventions |
| 5 · Intelligent collaboration | Can policies make better decisions under changing conditions? | Task specification, policies, baselines, ablations and data | Conclusions bounded by tested tasks, observations, communication and disturbances |

Stages express dependencies. Simulation, task design and research can proceed in parallel. Physical claims depend on acceptance of the relevant lower-level conditions. Record robot count, arena, speed, lighting and allowed initial error. Repeat affected checks after changing motors, camera, arena or software versions.

## When is a task complete? {#completion-rule}

Before a task, record its goal, inputs and outputs, scenarios, trial counts, metrics, thresholds and abort rules. On completion, save code revision, configuration, raw logs, results, anomalies and reproduction commands. Label successes, failures and aborts, reporting total and per-class counts. Decide before running how to treat logging failures or device faults and list them separately.

**The thresholds below are initial proposals, not measured platform capabilities.** Choose and freeze thresholds for the actual speed, arena and task. For each standard scenario, start with at least 10 valid trials, including at least 3 varied starting positions or headings. When physical time is limited, use 5 exploratory runs first, followed by formal trials under fixed conditions.

All four conditions must hold before declaring a stage ready.

1. Required tasks meet their predefined thresholds with traceable evidence.
2. Important failures have causes, reproduction conditions and a response. Document unresolved limitations.
3. Another person independently reproduces one run using the instructions.
4. State the interface and limits for the next stage, including speed, pose freshness, goal error and known blind spots.

Acceptance applies to tested conditions. Extend measurements before claiming a wider operating range.

## Stage 1 · Single-robot platform {#stage-one}

**Goal:** make the full path from power-on to stopping observable and reproducible.

| Task | Work and artifact | Initial completion criterion |
| --- | --- | --- |
| 1.1 Assembly and identity | Verify supply, fasteners, wiring, firmware environment, robot ID and tag ID. Create a robot record | 5 cold starts identify the same device, online state, binding and firmware correctly |
| 1.2 Wheel and feedback calibration | Measure counts, directions, effective diameter and track. Save configuration and readings | Correct signs, within 1% variation across 3 count and diameter measurements |
| 1.3 Localization acceptance | Calibrate intrinsics, extrinsics, tag dimensions and offsets. Measure position and heading at 9 points | In the declared area, position p95 ≤ 10 mm, heading p95 ≤ 3°, valid poses ≥ 99% |
| 1.4 Motion and stopping | Verify wheel directions lifted, then measure straight travel, pivot and stopping distance on the floor | 10 straight runs at 0.05 m/s without anomalies. Record speed error and maximum stopping distance, which fits the allocated distance |
| 1.5 Interruptions and records | Test command expiry, localization occlusion and server shutdown. Save reasons and logs | 3 repetitions each stop with a traceable cause. Recovery uses fresh input |

**Stage report:** deliver measurements, configuration and firmware revision, localization error distribution, speed and stopping tests, and anomalies. Reuse the result within tested speed, floor, camera and arena conditions. [Measurements](../hardware/bringup#measurement-procedures) · [Localization acceptance](./localization#measure-localization)

## Stage 2 · Multi-robot platform {#stage-two}

**Goal:** scale from two to four robots while distinguishing each robot's state, control and faults.

| Task | Work and artifact | Initial completion criterion |
| --- | --- | --- |
| 2.1 Replicate one robot | Complete stage 1 independently for each participant and maintain identity, firmware and calibration records | Every participant passes stage 1 with unique robot and tag IDs |
| 2.2 Two robots in parallel | Run independent low-speed straight and turning motions from separate starts. Record requests, feedback and trajectories | 10 valid trials identify both robots correctly, with no crossed actions or states. Both stop and release at the end |
| 2.3 Four-robot joint actions | Run joint actions with ample spacing and inspect each robot's online state, pose and acknowledgments | Complete 10 valid trials. Report per-robot pose validity, communication gaps and stops |
| 2.4 Interference and recovery | Test tag occlusion, one device disconnect, competing control requests and recovery | At least 3 repetitions per scenario. Responses match predefined expectations and causes are traceable |
| 2.5 Timing and capacity | Record state age, control period, telemetry intervals and recording drops for 2 and 4 robots | Report p50/p95/max and sample counts, complete logs, supported frequency and robot count |

**Stage report:** deliver per-robot records, identity mapping, integration results and timing statistics. Joint requests are processed together by the platform. Measure execution skew between robots. Set `ROBOT_ALLOW_UNLOCALIZED_CONTROL=0` when pose, boundary and spacing protection are required.

## Stage 3 · Reliable motion control {#stage-three}

**Goal:** turn a goal or reference path into repeatable differential-drive velocity commands. The platform supplies state and `v/omega`. The experiment supplies tracking, termination and evaluation.

| Task | Input → output | Initial completion criterion |
| --- | --- | --- |
| 3.1 Reach a pose | Current pose + target pose → `v/omega`, with distance and heading errors | 10 trials from each of 4 directions, final position ≤ 30 mm, heading ≤ 10°, success ≥ 90% |
| 3.2 Lines and arcs | Waypoints → commands, with reference and measured trajectories | 10 trials each, lateral error p95 ≤ 30 mm, final error ≤ 40 mm, report maximum error |
| 3.3 Path tracking | A path with lines, curves and a stop → continuous control | 10 trials on each of 3 paths, success ≥ 90%, within the predefined operating area |
| 3.4 Exceptions | Stale pose, computation timeout or unreachable goal → stop and result | At least 3 trials each, no continued commands from stale observations or old policy results, traceable termination |
| 3.5 Parameters and disturbances | Vary initial error, battery and floor conditions, record control cadence and duration | List passing and failing conditions and the controller's operating range, retaining every run |

Compute errors in the same world frame at the measured control point. Localization uncertainty contributes to position error, so thresholds must exceed measurement uncertainty. Compute success rate using predefined valid trials and list failures and aborts separately.

**Stage report:** deliver controller code, instructions, parameters, scenarios and per-run results. The next stage can call path tracking with known speed, error, cadence and failure semantics.

## Stage 4 · Multi-robot motion planning {#stage-four}

**Goal:** turn multi-robot goals into executable plans considering differential-drive motion, body dimensions and time. The planner chooses paths or velocities, the stage 3 tracker executes, and the platform provides its existing validation and stop protections.

| Task | Scenario and artifact | Initial completion criterion |
| --- | --- | --- |
| 4.1 Single-robot static planning | Reach a goal around known fixed obstacles, returning a path or unreachable result | At least 3 layouts with 10 trials each. Reachable success ≥ 90%, unreachable cases return within the deadline |
| 4.2 Two-robot crossing | Cross or exchange positions, comparing sequential passage and simultaneous planning | 10 trials per layout. Report success, minimum body clearance, waiting and protection interventions |
| 4.3 Multi-robot assignment and arrival | 2–4 robots reach goals, comparing fixed and centralized assignment | At least 10 trials per robot count. Report overall success, completion time, per-robot error and failure causes |
| 4.4 Dynamic changes | Change a goal, stop a robot or block a path, triggering replanning or waiting | At least 3 trials each. Return a new plan or stop within the preset time and record planning duration |
| 4.5 Stress and recovery | Vary density, pose gaps, planning cadence and tracking error | Report success against each condition and counts of planning failures, tracking failures and protective stops |

Choose minimum clearance and collision criteria before testing from measured body size, localization uncertainty and stopping distance. Obstacle state, path planning and collision evaluation require experiment-layer implementation. The current platform provides arena boundary and spacing protections. See [capabilities](./status).

**Stage report:** deliver scenarios, planner/tracker interfaces, constraints, computation time, trajectories and results. An intelligent policy can later provide goals or higher-level decisions while the planner exposes failures and interventions.

## Stage 5 · Intelligent control and collaboration {#stage-five}

**Goal:** compare policies under explicit information, action and resource limits.

| Task | Research question | Comparisons and completion evidence |
| --- | --- | --- |
| 5.1 Dynamic task allocation | How should robots divide work as jobs appear, disappear or change priority? | Compare nearest-distance, fixed-role and centralized assignment. Report completion, time, load balance and communication |
| 5.2 Cooperative coverage and search | How do robots cover an area or find targets within a time limit? | Compare random walk, fixed partition and no-communication policies. Report coverage over time, repeated coverage and discovery time |
| 5.3 Formation and transitions | Can local interactions maintain or change a formation? | Compare centralized and fixed-rule control. Report formation error, convergence time, spacing and interventions |
| 5.4 Reallocation after failure | Can remaining robots continue after one leaves or communication degrades? | Compare no reallocation and centralized reassignment. Report lost work, recovery time and message cost |
| 5.5 Learned policy transfer | How does a trained policy perform on unseen starts, disturbances and physical robots? | Fix train/test splits and weights, compare rule baselines. Report seeds, inference latency, success and failure scenarios |

Define robot count, initial conditions, task generation, local observations, communication range/rate/delay/loss, action cadence, termination and statistics first. An initial proposal is at least 3 independent seeds or task-instance groups, with at least 10 valid trials per group. Report each group and uncertainty. Choose primary metrics and thresholds before comparing methods.

`/api/state` currently exposes global state. Local-observation and limited-communication studies require an experiment-layer adapter and isolation checks. Record information used by evaluation and protection. Measure logical communication disturbances separately from server-to-device execution traffic. [Research validity](../design/research)

**Stage report:** deliver task specifications, policy and baseline implementations, train/test configuration, all run records, metrics and ablations. State protective interventions, missing observations, computation timeouts and untested conditions.

## One-page task report template {#task-summary}

Use the same table for handoff and deciding whether to advance.

| Item | Record |
| --- | --- |
| Task and owner | ID, objective, owner and date |
| Preconditions | Required stage results, robot and arena scope |
| Inputs and outputs | Observations, commands/paths, units, rates and deadlines |
| Conditions | Revisions, firmware, calibration, initial states, speed, arena and environment |
| Pass criteria | Primary metric, thresholds, trial count and failure/abort definitions |
| Results | Success/failure/abort counts, error or timing statistics, protective interventions |
| Evidence | Code and configuration, log paths, figures, reproduction commands, video or measurements |
| Open issues | Symptoms, scope, reproduction conditions and owner |
| Decision and handoff | Pass/fail and evidence, conditions and limits the next task may rely on |

For example, stage 3 pose reaching can use a 3 × 3 m arena and speeds ≤ 0.05 m/s, with 10 trials from each of four headings. Success means position error ≤ 30 mm, heading error ≤ 10° and stopping within the deadline. Record all 40 runs and trajectories, require at least 36 successes, list device-fault aborts separately and complete the required valid trials. Hand off the controller revision, goal interface, error distribution and failure conditions.
