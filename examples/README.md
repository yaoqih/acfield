# Control examples

Start the local demo server using the root README, then from the repository root:

```bash
robot_server/.venv/bin/python examples/velocity_control.py --duration 2
robot_server/.venv/bin/python examples/velocity_control.py --robots car-01 car-02 --duration 2
```

The example checks readiness, explicitly arms selected robots, submits joint velocities at approximately 10 Hz and requests disarming on exit. It does not reset global stop or take another controller's ownership. It refuses a hardware-mode server unless `--hardware` is explicit. Calibrate and validate hardware first. It is a bounded API example, not a navigation policy or research baseline.
