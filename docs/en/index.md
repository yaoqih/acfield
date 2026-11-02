# ACField

**An Open Multi-Robot Testbed for Multi-Agent Control.** Developed and maintained by **AClab — Algorithms and Collaboration Lab**.

ACField connects external AprilTag localization, a local control server, a web console and ESP32 differential-drive robots. The reference configuration uses four small robots in an indoor arena. Researchers can connect their own controllers through state and joint velocity interfaces.

## Start without hardware

Requirements: Python 3.11+ (3.12 recommended), Node.js 20.19+ or 22.12+, Git and optionally uv.

```bash
git clone https://github.com/yaoqih/acfield.git
cd acfield/robot_server
uv sync --extra test
npm --prefix frontend ci
npm --prefix frontend run build
./run.sh
```

Open **http://127.0.0.1:8000**. The default demo does not open the device UDP transport. Select a robot, explicitly arm it, then hold a direction button. Global stop locks all robots; releasing it does not re-arm them.

From the repository root, run a bounded example while the server remains running:

```bash
robot_server/.venv/bin/python examples/velocity_control.py --duration 2
```

## Design principles

The platform owns state, control ownership, command validation, execution feedback, fault stops and basic recording. Task definitions, training, rewards and paper-specific evaluation belong to the experiment layer.

A single owner of runtime state makes a small system easier to inspect. Each robot independently checks command lifetimes and runs wheel-speed control. Shared infrastructure does not imply a centralized policy: distributed policies require explicit observation and communication rules.

We distinguish requested actions, platform-modified actions, acknowledgments and measured motion. Safety intervention should be visible in research results, particularly when the protective layer has access to global state.

## Current status

This is a **development preview**. Software, protocol and firmware checks are automated. The V11 reference design includes editable sources and nominal geometry reports; physical assembly, calibration, timing and stopping performance still require measurement.

The demo is a lightweight interface test, not a validated training simulator or benchmark. A stable SDK, episode management, observation isolation and standardized tasks are future work. See the [status page](../guide/status) and [roadmap](../community/roadmap).

## Explore

- [Quick start](../guide/quickstart) and [control integration](../guide/control).
- [Design philosophy](../design/philosophy), [architecture](../design/architecture) and [tradeoffs](../design/decisions).
- [Reference hardware](../hardware/overview) and [bring-up](../hardware/bringup).
- [HTTP interface](../reference/api), [protocol](../reference/protocol) and [recording](../guide/recording).

Detailed guides are currently in Chinese. English translations and reproducibility reports are welcome. The project uses Apache-2.0 for original material; third-party assets retain their licenses. Cite the repository and the commit or release used. [GitHub →](https://github.com/yaoqih/acfield)
