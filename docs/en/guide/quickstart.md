# Quick start

Explicitly select the hardware-free demo to check the console and API. Demo mode does not open the device UDP transport. The launch scripts default to LAN hardware operation; the commands below override those defaults.

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
ROBOT_MODE=demo ROBOT_HOST=127.0.0.1 ROBOT_UDP_HOST=127.0.0.1 \
  ROBOT_ALLOW_UNLOCALIZED_CONTROL=0 ./run.sh
```

Open the [console](http://127.0.0.1:8000). For later launches, repeat the same environment overrides inside `robot_server/`; bare `./run.sh` uses the hardware defaults.

Windows PowerShell:

```powershell
git clone https://github.com/yaoqih/acfield.git
cd acfield
uv sync --python 3.12 --extra test
cd robot_server
$env:ROBOT_MODE = "demo"
$env:ROBOT_HOST = "127.0.0.1"
$env:ROBOT_UDP_HOST = "127.0.0.1"
$env:ROBOT_ALLOW_UNLOCALIZED_CONTROL = "0"
.\run.bat
```

The first launch installs frontend dependencies and builds the page when needed. For later launches run `.\run.bat` in `robot_server` in the same PowerShell session; set the variables again in a new terminal. Press Ctrl+C to stop both services. Camera and device networking require validation on the actual Windows machine.

Without uv:

```bash
cd acfield
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
cd robot_server
ROBOT_MODE=demo ROBOT_HOST=127.0.0.1 ROBOT_UDP_HOST=127.0.0.1 \
  ROBOT_ALLOW_UNLOCALIZED_CONTROL=0 ./run.sh
```

The commands without uv above target macOS/Linux. On Windows, use the uv instructions to share the root `.venv`.

## First interaction {#first-interaction}

1. Select a robot in the arena and inspect its state on the right.
2. Drag the joystick directly; the server automatically performs the device handshake. Releasing it requests a stop. On a computer, you can also focus the joystick and hold the arrow keys.
3. Press Space outside an input, or use global stop, to lock every robot.
4. After releasing global stop, use fresh joystick input to move again. Old motion is not resumed.

The joystick is relative to the robot's nose: up drives forward, down reverses, and diagonals produce arcs through different wheel targets. Forward-right requests a faster left wheel; forward-left requests a faster right wheel. In reverse, right/left still turns the nose right/left. Travelling arcs retain a same-direction inner-wheel target of at least 30% of the mean wheel speed. Near horizontal input, steering blends smoothly into a counter-rotating pivot, passing through zero on the inner wheel during that transition. Normal firmware 0.2.8 defaults to open-loop PWM proportional to wheel targets; actual speed varies with battery and load, and very low output may not keep a wheel turning.

The joystick sends the latest target over an ordered WebSocket every 25 ms (40 Hz) with a 300 ms TTL. Page blur or visibility changes alone do not disarm. Key release or loss of keyboard focus clears held keys; touch release or pointer cancellation ends the current input. The server independently checks expiry. Hardware operation waits for browser and device clock synchronization. Demo mode applies targets immediately and cannot establish physical latency.

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

For phone control, use `http://SERVER_LAN_IP:8000/mobile`. The demo commands bind locally; follow [configuration](./configuration#startup-addresses-and-lan-access) to enable LAN access.

## Next steps {#next-steps}

- Understand the choices: [Design philosophy](../design/philosophy).
- Replace the example policy: [Controller integration](./control).
- Configure storage and listeners: [Configuration](./configuration).
- Prepare physical robots: [Reference hardware](../hardware/overview).
