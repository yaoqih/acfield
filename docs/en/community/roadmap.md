# Roadmap

The roadmap is organized by acceptance conditions, without dates for unverified capabilities. First make the shared platform understandable and runnable, then add research-environment responsibilities.

## Now · Development preview {#now-development-preview}

- Control server, web console, independent vision, firmware and V11 reference design.
- Clear guides, interface semantics, design tradeoffs and evidence boundaries.
- Cross-component protocol tests, software checks and four firmware builds.
- Continuously published GitHub Pages documentation.
- Independently installed synchronous Python SDK with typed state, joint actions, control sessions and conditional release.

See [capabilities and evidence](../guide/status) for current boundaries.

## Next · A reproducible reference platform {#next-a-reproducible-reference-platform}

Acceptance means another user can build the reference combination from public materials and obtain interpretable results.

- Measured first-article dimensions, wiring, motor and camera calibration.
- One-, two- and four-robot motion and failure checks.
- SDK lifecycle, timeout and error behavior validated in external experiments before stable compatibility commitments.
- One complete physical reference example with log interpretation.
- Versioned software/hardware compatibility combinations.

## As research needs develop · Experiment environment {#as-research-needs-develop-experiment-environment}

- Fixed-step differential-drive simulation with configurable disturbances.
- A small set of tasks, baselines, episodes and termination rules.
- Observation/action/execution associations, evaluation and replay.
- Observation and communication isolation defined by experiment rules.
- Optional PettingZoo or ROS 2 integration when actual users need it.

Paper-specific methods, training settings and weights live in separate repositories pinned to an ACField revision. Add capabilities to the platform once multiple experiments demonstrate their general use.

## How priorities are chosen {#how-priorities-are-chosen}

Bring reproducible setup problems, measurements or concrete workflows to issues. Reproduction and failure behavior take priority. New abstractions need at least one specific use case. Reconsider extraction only when a module has independent users, maintainers and release needs.
