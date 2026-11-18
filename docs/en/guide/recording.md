# Recording and reproducibility

Save **run conditions, raw events, and analysis results** for each experiment. [Your first experiment](./first-experiment) provides executable collection and analysis commands.

## File locations {#what-is-recorded}

Each startup creates `robot_server/data/runs/<run_id>/` by default. With a custom `ROBOT_DB`, logs follow the database parent directory. `ROBOT_LOG_DIR` overrides the root. Read `run_id` from `GET /api/health`.

```text
runs/<run_id>/
├── config.json       Startup session, mode, settings, vision URL, protocol
└── events.jsonl      Append-only events, one JSON object per line
output/first-run/
├── experiment.json  One experiment, written by the example
├── summary.json     Analysis results
├── trajectories.csv
└── trajectories.png
```

One server run can contain multiple experiments. `config.json` captures startup settings. Read `configuration` events for later changes. The log currently has no independent schema version. Pin the platform commit when parsing and retain original files.

## Event schema {#event-schema}

```json
{"time": 1800000000.125, "monotonic": 100.125, "kind": "pose", "data": {"robot_id": "car-01", "x": 0.84, "y": 0.84, "theta": 0.0, "at": 100.12}}
```

`time` is server Unix seconds at enqueueing. `monotonic` is server-process monotonic seconds. `kind` selects the event type and `data` holds its payload.

| `kind` | Main `data` fields and purpose |
| --- | --- |
| `startup` | `session`, initial session |
| `configuration` | `session`, `settings`, complete saved configuration |
| `mode` | `session`, `mode`, new session after switching modes |
| `event` | `message`, readable status |
| `control` | `owner`, `requested`, `accepted`, with `applied` on success or `reason` on rejection |
| `command` | Constructed packet with `session`, `robot_id`, `seq`, `action`, `v`, `omega`, `ttl_ms` and device echo fields for hardware |
| `telemetry` | Device packet with `robot_id`, `boot_id`, `ack_session`, `ack_seq`, speeds and counts. Demo has no physical telemetry |
| `pose` | `robot_id`, `x`, `y`, `theta`, `at`. Position is the axle midpoint and `at` is server monotonic seconds |
| `stop` | `robot_id`, `reason`, server stop cause |
| `udp_rejected` | `endpoint`, `reason`, `fields`, rejection clues |

These examples show accepted and rejected requests. `applied` describes the server-selected target. Check device acknowledgment and measured motion separately.

```json
{"time": 1800000000.13, "monotonic": 100.13, "kind": "control", "data": {"owner": "example-controller", "requested": {"car-01": {"v": 0.6, "omega": 0.0, "ttl_ms": 300, "execute_at_ms": null}}, "accepted": true, "applied": {"car-01": {"v": 0.5, "omega": 0.0}}}}
```

```json
{"time": 1800000000.14, "monotonic": 100.14, "kind": "control", "data": {"owner": "example-controller", "requested": {"car-01": {"v": 0.05, "omega": 0.0, "ttl_ms": 300, "execute_at_ms": null}}, "accepted": false, "reason": "global stop latched"}}
```

## Select one experiment {#suggested-experiment-manifest}

The velocity example writes `experiment.json` with `schema_version=1` when given `--output`.

| Fields | Purpose |
| --- | --- |
| `run_id`, `session`, `mode`, `robots` | Identify logs, session and participants |
| `start_time`, `end_time` | Initial/final state timestamps in server Unix seconds for log selection |
| `requested`, `initial`, `final` | Parameters and initial/final states. Early failures may omit `final` |
| `result`, `error` | `completed` or `aborted`, with a reason on failure |
| `recording_dropped`, `recording_error` | Recording health at completion, potentially absent on early failure |
| `platform_commit`, `worktree_dirty` | Git revision and dirty status of the example checkout, `null` if unavailable |

Run the example and server from the same checkout. For distributed deployments, record server and firmware commits separately. Add hardware revision, calibration files and hashes, controller revision, task parameters, starting poses, battery, floor conditions and repeat counts for hardware experiments.

The analyzer locates logs by `run_id`, selects the interval using server Unix time, and measures trajectory intervals using pose `at`. It rejects aborted runs and session changes within the interval. Counts cover relevant events for participating robots.

## Correlate actions, acknowledgments and motion {#correlate-events}

Match command `session + robot_id + seq` to telemetry `ack_session + ack_seq` and verify `boot_id`. ACK confirms protocol processing. Inspect encoders and poses for motion. A cumulative latest ACK cannot prove separate execution of every intermediate action.

A `command` can precede its `control` event. Adjacent-row pairing is unreliable. Pose events currently carry no action ID. Measuring observation-to-execution latency requires experiment-owned observation/action IDs, sampling timestamps, execution feedback and clock uncertainty. See [time bases](../reference/state#time-bases).

## Recording integrity {#recording-integrity}

Check `/api/health` before and after running for `recording_dropped=0` and `recording_error=null`. The queue holds 2048 events and drops incoming events when full. Shut down normally and wait for writing to finish before copying or analyzing logs.

`gaps_over_200ms` counts localization gaps, which path length excludes. Camera gaps can occur while recording remains healthy. Inspect both indicators.

## Repeatability and archiving {#discuss-repeatability-at-each-layer}

Demo integrates constant-velocity arcs using actual host intervals, capped at 100 ms per step. Scheduling and command arrival times affect trajectories. Fixed-step evaluation requires experiment-owned initial states, step size, seeds and action sequences.

For hardware, report position/heading error, initial error, repeat count and treatment of abnormal runs. Physical replay also requires models and an experiment definition.

## Data and repositories {#data-and-repositories}

Small public demo datasets and figures can accompany documentation with mode and revision recorded. Store videos, models and research datasets in Releases or data archives with hashes and licenses. Keep personal configuration, SQLite files and device credentials locally.
