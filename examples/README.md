# Control examples

Start the local demo server using the root README, then from the repository root:

```bash
uv pip install --python robot_server/.venv/bin/python -e ./sdk/python
robot_server/.venv/bin/python examples/velocity_control.py --duration 2
robot_server/.venv/bin/python examples/velocity_control.py --robots car-01 car-02 --duration 2
```

The example uses the [Python SDK](../sdk/python/README.md) to check readiness, wait for selected robots to arm, submit joint velocities at approximately 10 Hz and request conditional release on exit. It does not reset global stop or take another controller's ownership. It refuses a hardware-mode server unless `--hardware` is explicit. Calibrate and validate hardware first. It is a bounded API example, not a navigation policy or research baseline. Without uv, install with the same virtual environment's `python -m pip install -e ./sdk/python`.
