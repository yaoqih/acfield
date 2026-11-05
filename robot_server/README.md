# ACField local runtime

FastAPI state/control service and Vue 3 / TypeScript console. The launch scripts default to hardware mode on the LAN; direct `python -m backend.app` defaults to local demo mode. Demo mode needs no camera or robots and does not open the device UDP transport.

## Start

Requirements: Python 3.11+ (3.12 recommended), Node.js 20.19+ or 22.12+.

```bash
cd acfield
uv sync --python 3.12 --extra test
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
cd robot_server
./run.sh
```

Open http://127.0.0.1:8000. Reuse `./run.sh` after the frontend is built. Configuration is created in `data/config.sqlite3` and runs are recorded in `data/runs/` by default; neither belongs in version control.

On Windows, install Node.js and uv, then run in PowerShell:

```powershell
cd acfield
uv sync --python 3.12 --extra test
cd robot_server
.\run.bat
```

The Windows launcher builds the frontend if needed, starts both services and stops them on Ctrl+C. The launch scripts default `ROBOT_MODE` to `hardware` and both `ROBOT_HOST` and `ROBOT_UDP_HOST` to `0.0.0.0`; existing environment values take precedence. Camera and device networking need validation on the target Windows machine.

`./run.sh` also starts `apriltag_live.py` on `127.0.0.1:8765` and stops it when the control server exits. Open **Experiment settings → Camera and vision** to select a camera and edit, save and calibrate its settings. Demo mode can configure a real camera while robot positions remain simulated. The first start leaves the camera disconnected; later starts restore its saved connection state. Vision settings are saved in `../output/vision-settings.json`.

Set `ROBOT_VISION_PORT` to change the local vision port, or `ROBOT_START_VISION=0` to use an independently running vision service. The console stores its vision URL; `ROBOT_VISION_URL` explicitly overrides the stored address on startup. `ROBOT_VISION_RUNTIME_CONFIG` changes the vision settings file used by the script.

The console can switch the current session between demo and hardware modes. Switching stops and locks all robots and starts or closes the device transport. When a vision URL is configured, switching to hardware synchronizes the robot dimensions and arena with the vision service first; a failed sync leaves the fleet locked. Hardware mode requires device binding and, by default, calibrated live localization. A restart uses `ROBOT_MODE` again (launch scripts: `hardware`; direct module: `demo`). On a phone, open the server's LAN address followed by `/mobile` for the dedicated remote-control page. Select a robot and use the touch joystick: vertical and horizontal displacement control linear and angular speed in proportion to the robot's effective speed limits. Releasing it stops the selected robot. Start with `ROBOT_HOST=0.0.0.0` for LAN access, and use `ROBOT_UDP_HOST=0.0.0.0` for hardware on the LAN.

`./run.sh` and `python -m backend.app` print console/API addresses and the detected
host IPv4. To connect from another computer's Python SDK, start with
`ROBOT_HOST=0.0.0.0 ./run.sh` and use the printed LAN URL. The direct module defaults to a local listener; the launch scripts default to LAN access. Addresses come from hostname resolution and the routing table; choose
the address reachable on your experiment network, especially when using a VPN.

## Hardware mode

`./run_hardware.sh` (Windows: `run_hardware.bat`) explicitly selects hardware mode and starts the vision service unless overridden. Complete firmware and camera calibration before using hardware mode:

```bash
ROBOT_MODE=hardware ROBOT_UDP_HOST=0.0.0.0 ./run.sh
```

Use one process and one worker. This local/LAN service has no account authentication or authenticated UDP transport. The `X-Control-ID` header manages ownership only. Device arming and finite command lifetimes remain required. Set `ROBOT_ALLOW_UNLOCALIZED_CONTROL=1` before launch only for manual operation without localization: it skips pose freshness, arena boundary and inter-robot distance checks, while binding, telemetry freshness, command expiry and ownership expiry still apply. The default is `0`. Restart after changing it. Server robot speed defaults are 1 m/s and 3 rad/s, capped by device-reported limits; stored robot configurations retain their existing limits.

## Development

```bash
cd ..
uv run --python 3.12 --extra test pytest -q
cd ../sdk/python
uv run --python 3.12 pytest -q
npm --prefix robot_server/frontend run dev
npm --prefix robot_server/frontend run build
```

The backend tests include the actual firmware parser contract; install a host C++ compiler and PlatformIO's ArduinoJson first. CI makes missing contract dependencies an error.

From the repository root, run `npm --prefix robot_server/frontend run build` and `npm run console:test` for the joystick and settings browser checks. They use an isolated demo server and temporary database; install Chromium with `npx playwright install chromium` on the first run.

| Module | Responsibility |
| --- | --- |
| `backend/app.py` | HTTP, WebSocket, lifecycle and static frontend |
| `backend/state.py` | State, ownership, arming and joint-action validation |
| `backend/safety.py` | Conservative boundary / inter-robot protective stops |
| `backend/udp.py` | Device transport |
| `backend/vision.py` | External AprilTag adapter |
| `backend/simulator.py` | Lightweight demo motion |
| `backend/recording.py` | Bounded JSONL event recording |
| `backend/storage.py` | SQLite configuration |

Full documentation: [configuration](https://yaoqih.github.io/acfield/guide/configuration), [API](https://yaoqih.github.io/acfield/reference/api), [device protocol](https://yaoqih.github.io/acfield/reference/protocol), [architecture](https://yaoqih.github.io/acfield/design/architecture).
