# Recording and reproducibility

Recording helps explain what a controller requested, what the platform allowed, what devices reported and why motion stopped.

## What is recorded {#what-is-recorded}

Each server launch creates a separate `runs/` directory beside the database. Configuration and events are separate. `events.jsonl` stores one JSON object per line, including poses, commands, telemetry, stops and configuration changes. Control records include raw actions, clamps and rejection reasons.

A bounded background queue handles writing. `/api/health` exposes the run ID, dropped-event count and write errors. Queue overflow or failed writes affect evidence completeness; experiments should define when to abort or mark a run invalid.

These are engineering logs. A server run ID is not automatically a research episode ID.

## Suggested experiment manifest {#suggested-experiment-manifest}

```yaml
experiment: formation-reference
platform_commit: <git commit>
firmware_commit: <git commit>
hardware_revision: V11-first-article
calibration_id: <measured configuration hash>
controller: <method and version>
scenario: <initial poses and task parameters>
seed: <simulation seed, if applicable>
run_id: <server run id>
episode_id: <experiment-owned id>
result: success | failure | aborted
```

This is a suggested record, not an input supported by the current parser. Also preserve actual policy observations/actions, inference time, messages and termination conditions.

## Discuss repeatability at each layer {#discuss-repeatability-at-each-layer}

Seeds and fixed timesteps constrain simulation but do not eliminate physical placement, friction, battery or vision changes. Record initial error, environment, repetitions and handling of abnormal runs.

Logs currently provide neither complete physical re-execution nor one-click trajectory replay. Visualization and episode evaluation may build on them later; event files alone are not a complete research reproduction framework.

## Data and repositories {#data-and-repositories}

Do not commit local SQLite files, Wi-Fi secrets or long raw videos. Small public examples may accompany releases. Store larger datasets, videos and weights in releases or data archives with checksums, licensing and generating revisions.
