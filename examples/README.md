# Control examples

Start the local demo server using the root README, then from the repository root:

```bash
.venv/bin/python examples/velocity_control.py --duration 2
.venv/bin/python examples/velocity_control.py --robots car-01 car-02 --duration 2
```

To save and analyze an experiment, choose a fresh output directory and run from the same checkout as the server.

```bash
uv run --frozen python examples/velocity_control.py --robots car-01 car-02 \
  --duration 2 --v 0.05 --omega 0.2 --output output/first-run
# Stop the server and wait for shutdown to finish writing the log.
uv run --frozen python examples/analyze_run.py output/first-run --plot
```

The manifest records the server run/session, parameters, initial/final states, result, recording health and checkout revision. Analysis writes `summary.json`, `trajectories.csv` and, with matplotlib, `trajectories.png`. For custom server logs, pass `--logs /path/to/log/root`. Aborted runs require inspection before analysis. Gaps over 200 ms break the plotted line and are excluded from path length.

The downloadable [demo dataset](../docs/public/examples/first-run) includes its original event log. Analyze it with `uv run --frozen python examples/analyze_run.py docs/public/examples/first-run --logs docs/public/examples/first-run/logs --plot`. Regenerate into a new directory with `uv run --frozen python tools/documentation_demo.py --output output/docs-demo`. The [bilingual tutorial](https://yaoqih.github.io/acfield/en/guide/first-experiment) explains expected results.

The example uses the [Python SDK](../sdk/python/README.md) to check readiness, wait for selected robots to arm, submit joint velocities at approximately 10 Hz and request conditional release on exit. It does not reset global stop or take another controller's ownership. It refuses a hardware-mode server unless `--hardware` is explicit. Calibrate and validate hardware first. It is a bounded API example, not a navigation policy or research baseline. For independent algorithm environments, install the SDK with `python -m pip install -e ./sdk/python`.
