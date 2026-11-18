# Quick start

**Get four simulated robots moving.** Then inspect the API and complete an experiment with saved records.

## Requirements and startup {#requirements}

Install Git, Python 3.11+ (3.12 recommended), Node.js 20.19+ or 22.12+, and [uv](https://docs.astral.sh/uv/). These commands start a local demo.

::: code-group
```bash [macOS / Linux]
git clone https://github.com/yaoqih/acfield.git
cd acfield
uv sync --frozen --python 3.12 --extra test
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
cd robot_server
ROBOT_MODE=demo ROBOT_HOST=127.0.0.1 ROBOT_START_VISION=0 \
  ROBOT_ALLOW_UNLOCALIZED_CONTROL=0 ./run.sh
```

```powershell [Windows PowerShell]
git clone https://github.com/yaoqih/acfield.git
cd acfield
uv sync --frozen --python 3.12 --extra test
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
cd robot_server
$env:ROBOT_MODE = "demo"
$env:ROBOT_HOST = "127.0.0.1"
$env:ROBOT_START_VISION = "0"
$env:ROBOT_ALLOW_UNLOCALIZED_CONTROL = "0"
.\run.bat
```
:::

After `Application startup complete`, open [http://127.0.0.1:8000](http://127.0.0.1:8000). Expect an arena with four online robots. Press Ctrl+C to exit. Repeat these overrides on later launches. Bare launch scripts default to LAN hardware mode.

| Environment | Verification scope |
| --- | --- |
| Ubuntu, Python 3.12, Node 22 | CI covers server, vision, frontend, docs and browser workflows |
| Ubuntu, Python 3.11 / 3.12 / 3.13 | SDK installation and actual API integration tests |
| macOS, Python 3.12 | Local software and browser checks, with per-device camera acceptance |
| Windows PowerShell | Launch script provided. Camera, drivers and device networking await machine-specific verification |

See [Python SDK installation](./python-sdk#installation) for independent environments and pip setup. See [Localization](./localization) to prepare cameras.

## First interaction {#first-interaction}

1. Select a robot and check that it is online with a valid pose.
2. Drag the joystick. Up drives forward, down reverses, and sides turn. Release to request a stop.
3. Activate global stop and confirm every robot stops.
4. Release global stop and provide fresh input to move again.

Keyboard input and steering response are covered in [Manual control](./manual-control). The phone entry point is `/mobile`. See [listener configuration](./configuration#startup-addresses-and-lan-access) for LAN access.

## Inspect the API {#inspect-the-api}

Open another terminal.

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/state
```

Expect `status="ok"`, `mode="demo"`, `ready=true`, and `recording_dropped=0` in health. State should contain four robots with `online=true` and `visible=true`. Open the [interactive API documentation](http://127.0.0.1:8000/docs) to explore endpoints.

## Next steps {#next-steps}

- **Complete an experiment** with two robots, saved logs and a plot. [Your first experiment](./first-experiment)
- **Integrate a policy** using state, coordinates and control lifecycle. [Controller integration](./control) · [State dictionary](../reference/state) · [Coordinates](../reference/coordinates)
- **Prepare hardware** by identifying the revision and measuring each vehicle. [Compatibility](../hardware/compatibility) · [Bring-up](../hardware/bringup)
