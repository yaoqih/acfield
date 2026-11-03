# ACField local runtime

FastAPI state/control service and Vue 3 / TypeScript console. Default demo mode needs no camera or robots and does not open the device UDP transport.

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

`./run.sh` and `python -m backend.app` print console/API addresses and the detected
host IPv4. To connect from another computer's Python SDK, start with
`ROBOT_HOST=0.0.0.0 ./run.sh` and use the printed LAN URL. The default listener is
local only. Addresses come from hostname resolution and the routing table; choose
the address reachable on your experiment network, especially when using a VPN.

## Hardware mode

Complete firmware and camera calibration before using hardware mode:

```bash
ROBOT_MODE=hardware ROBOT_UDP_HOST=0.0.0.0 ROBOT_VISION_URL=http://127.0.0.1:8765 ./run.sh
```

Use one process and one worker. This local/LAN service has no account authentication or authenticated UDP transport. The `X-Control-ID` header manages ownership only. Device arming, fresh camera localization and finite command lifetimes remain required.

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
