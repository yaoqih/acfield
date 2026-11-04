# Quick start

Start with the hardware-free demo to check the console and API. The default mode does not open the device UDP transport.

## Requirements {#requirements}

Install Git, Python 3.11+ (3.12 recommended) and Node.js 20.19+ or 22.12+. [uv](https://docs.astral.sh/uv/) is recommended for the Python environment.

macOS / Linux:

```bash
git clone https://github.com/yaoqih/acfield.git
cd acfield
uv sync --python 3.12 --extra test
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
cd robot_server
./run.sh
```

Open the [console](http://127.0.0.1:8000). For later launches, run `./run.sh` inside `robot_server/`.

Windows PowerShell:

```powershell
git clone https://github.com/yaoqih/acfield.git
cd acfield
uv sync --python 3.12 --extra test
cd robot_server
.\run.bat
```

The first launch installs frontend dependencies and builds the page when needed. For later launches run `.\run.bat` in `robot_server`; press Ctrl+C to stop both services. Camera and device networking require validation on the actual Windows machine.

Without uv:

```bash
cd acfield
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
cd robot_server
./run.sh
```

The commands without uv above target macOS/Linux. On Windows, use the uv instructions to share the root `.venv`.

## First interaction {#first-interaction}

1. Select a robot in the arena and inspect its state on the right.
2. Arm the robot, then drag the joystick. Releasing it requests a stop. On a computer, you can also focus the joystick and hold the arrow keys.
3. Press Space outside an input, or use global stop, to lock every robot.
4. After releasing global stop, explicitly arm the robot again before moving.

When the page loses focus or becomes hidden it stops renewing commands and requests a stop. The server independently checks expiry. Joystick commands renew every 90 ms with a 300 ms TTL.

## Inspect the API {#inspect-the-api}

In another terminal:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/state
```

Open the [interactive API documentation](http://127.0.0.1:8000/docs). With the server running and global stop released, open another terminal at the repository root and run the single-robot example. It controls `car-01` by default, then requests a stop and disarms after two seconds.

```bash
# macOS / Linux
.venv/bin/python examples/velocity_control.py --duration 2
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe examples\velocity_control.py --duration 2
```

The example refuses hardware mode by default. Real robots require explicit `--hardware` and prior [bring-up](../hardware/bringup).

Without uv, use `python -m pip install -e ./sdk/python` in your active environment, then run the example with that same Python. See the [Python SDK](./python-sdk) for installation into an independent algorithm environment.

## Next steps {#next-steps}

- Understand the choices: [Design philosophy](../design/philosophy).
- Replace the example policy: [Controller integration](./control).
- Configure storage and listeners: [Configuration](./configuration).
- Prepare physical robots: [Reference hardware](../hardware/overview).
