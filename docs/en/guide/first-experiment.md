# Complete your first experiment

**Run two demo robots, save the records, and plot their trajectories.** Allow about five minutes. Start the server using [Quick start](./quickstart), then run the following commands from the repository root.

## Run and save {#run-and-save}

Keep the server running, release global stop, and close other pages controlling these robots.

<!-- docs-test: experiment-command -->
```bash
uv run --frozen python examples/velocity_control.py \
  --robots car-01 car-02 --duration 2 --v 0.05 --omega 0.2 \
  --output output/first-run
```

Expect `Controlling car-01, car-02 for 2 s`, `Experiment completed`, and the manifest path. Both robots follow slow arcs for about two seconds, then request a stop and release ownership. `output/first-run/experiment.json` stores parameters, initial/final states, server run ID, session, and code revision. Use a new output directory for every run.

If the result is `aborted`, read `error` in the manifest and follow [Troubleshooting](./troubleshooting). Global stop, ownership conflicts, and expired localization can interrupt the example.

## Analyze and plot {#analyze-and-plot}

Press Ctrl+C in the server terminal and wait for shutdown so the log finishes writing. Then run the analyzer.

<!-- docs-test: analysis-command -->
```bash
uv run --frozen python examples/analyze_run.py output/first-run --plot
```

For a custom log directory, add `--logs /your/log/root`. Outputs appear in the experiment directory.

| File | Contents |
| --- | --- |
| `experiment.json` | Task parameters, revision, completion result, initial/final states |
| `summary.json` | Sample counts, observed duration, path length, displacement, pose gaps over 200 ms |
| `trajectories.csv` | Per-robot elapsed time, world X/Y, heading |
| `trajectories.png` | Equal-aspect world trajectories, start circles and end crosses |

Two seconds at 0.05 m/s gives an ideal path of about **0.10 m**. Arming and host scheduling introduce variation. Check scale and gaps before comparing errors. The analyzer skips intervals exceeding 200 ms and breaks the plotted line at each gap, which can underestimate path length.

![Two-robot trajectories generated from actual demo logs](/examples/first-run/trajectories.png)

This figure comes from one demo run of the repository example. Download the [manifest](/examples/first-run/experiment.json), [summary](/examples/first-run/summary.json), and [trajectory table](/examples/first-run/trajectories.csv) to inspect the workflow and file formats. Measure physical performance separately.

Original events are included under `docs/public/examples/first-run/logs/`. Inspect them without starting a server.

```bash
uv run --frozen python examples/analyze_run.py docs/public/examples/first-run \
  --logs docs/public/examples/first-run/logs --plot
```

## Replace the policy {#replace-the-policy}

Inside the loop in `examples/velocity_control.py`, use `state` to compute each robot's `Velocity`. Check `robot.online`, `robot.visible`, and `pose_age_ms` before using observations. See the [state dictionary](../reference/state).

Keep the approximately 100 ms command cadence. A policy that exceeds the 300 ms command lifetime can cause a stop. Record inference duration as you extend the policy. Submit all robot targets together with `control.commands(actions)`.

For hardware, complete [bring-up](../hardware/bringup) and explicitly add `--hardware`. Save firmware version, hardware revision, calibration files, policy revision, and environmental conditions. See [Recording and reproducibility](./recording) for log fields and correlation rules.
