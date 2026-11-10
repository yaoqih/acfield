# Configuration

Startup defaults depend on the entry point. `./run.sh` / `.\run.bat` select LAN hardware mode and allow manual control without localization. Direct `python -m backend.app` selects a local demo. For hardware-free use, follow the explicit overrides in [quick start](./quickstart).

The console can switch between demo and hardware for the current process. Switching stops robots, activates global stop and replaces the session. Release global stop and arm again before motion. A restart uses `ROBOT_MODE`. The phone remote is at `http://SERVER_LAN_IP:8000/mobile`.

## Server environment variables {#server-environment-variables}

Defaults below distinguish direct backend startup from the launch scripts. Existing environment values take precedence.

| Variable | Direct backend / launch-script default | Purpose |
| --- | --- | --- |
| `ROBOT_MODE` | `demo` / `hardware` | Demo opens no device UDP; hardware runs no simulator |
| `ROBOT_HOST` | `127.0.0.1` / `0.0.0.0` | Control HTTP bind address |
| `ROBOT_PORT` | `8000` | Control HTTP port |
| `ROBOT_UDP_HOST` | `127.0.0.1` / `0.0.0.0` | Device UDP bind address |
| `ROBOT_UDP_PORT` | `9999` | Device UDP port |
| `ROBOT_ALLOW_UNLOCALIZED_CONTROL` | `0` / `1` | `1` skips pose freshness, arena boundary and robot-spacing checks; restart after changing |
| `ROBOT_VISION_URL` | Unset | Explicit override of the saved vision URL |
| `ROBOT_DEFAULT_VISION_URL` | Unset / `http://127.0.0.1:8765` | Fallback only without a saved URL; scripts follow the vision port |
| `ROBOT_START_VISION` | Script only, `1` | `0` skips starting local vision |
| `ROBOT_VISION_PORT` | Script only, `8765` | Local vision port |
| `ROBOT_VISION_RUNTIME_CONFIG` | Script only, unset | Override the vision profile path; default is repository-root `output/vision-settings.json` |
| `ROBOT_NTP_SERVER` | `pool.ntp.org` | Attempt synchronization every 300 s; empty disables it; offline operation retains the local-time mapping |
| `ROBOT_DB` | `robot_server/data/config.sqlite3` | Persistent configuration |
| `ROBOT_LOG_DIR` | `runs/` beside the database | Control-server logs |

Unlocalized control still requires binding, fresh telemetry, no fault, explicit arming, ownership and finite command lifetimes. Position-based protection is disabled; operation in this mode does not validate localization. Set `ROBOT_ALLOW_UNLOCALIZED_CONTROL=0` for experiments that require it. Inspect `allow_unlocalized_control` in `/api/state` for the active value.

## Startup addresses and LAN access {#startup-addresses-and-lan-access}

Startup inside `robot_server/` prints console/API URLs and detected host IPv4 addresses. Scripts already bind to the LAN by default. To share only a demo server with another computer, run:

```bash
ROBOT_MODE=demo ROBOT_HOST=0.0.0.0 ROBOT_ALLOW_UNLOCALIZED_CONTROL=0 ./run.sh
```

Pass a reachable `LAN / SDK` URL to `Client("http://HOST_IP:8000")`; append `/mobile` for the phone remote. Hostname and routing-table detection may include VPN interfaces. Printing an address does not change the listener. For direct backend startup, set `ROBOT_HOST=0.0.0.0` to enable LAN control HTTP access.

## Camera vision service {#camera-vision-service}

`./run.sh` / `.\run.bat` start both services and close their vision process on exit. `python -m backend.app` does not start vision. The first launch leaves the camera disconnected; later launches restore the saved connection state. A demo server can configure a physical camera while robot positions remain simulated.

Under **Experiment settings → Camera and vision**, read the profile, refresh devices and select a camera. Camera IDs belong to the vision computer. Capture resolution and frame rate are requests; inspect actual image dimensions and capture rate. Follow [localization and calibration](./localization#calibration-order) for intrinsics and world extrinsics. The separate calibration page provides ChArUco capture and solving.

Change `ROBOT_VISION_PORT` if occupied. For an independent service, set `ROBOT_START_VISION=0` and save its URL. The stock `apriltag_live.py` binds only to `127.0.0.1`; using it across computers requires controlled forwarding or a separate deployment arrangement. `ROBOT_HOST` affects the control service only.

The default profile is repository-root `output/vision-settings.json`. A custom relative path is resolved from the vision process working directory (`robot_server/` for the scripts). `apriltag_live.json` supplies initial defaults and is not overwritten by runtime edits. Preview width/rate affect MJPEG display only, reset on restart and do not change capture or detection settings.

Disarm all robots before direct calibration. Afterwards, reload the camera profile in the control console before saving so an old draft cannot overwrite new intrinsics. Back up measured intrinsics, coordinates and tag sizes. Use **Verify and load** after restarting to validate world extrinsics again.

## Hardware-mode example {#hardware-mode-example}

After hardware acceptance and camera calibration, start inside `robot_server/` with localization protection enabled:

```bash
ROBOT_MODE=hardware ROBOT_HOST=0.0.0.0 ROBOT_UDP_HOST=0.0.0.0 \
  ROBOT_ALLOW_UNLOCALIZED_CONTROL=0 ./run.sh
```

`./run_hardware.sh` / `.\run_hardware.bat` select hardware explicitly but inherit the main script's unlocalized default; also set the variable to `0` when localization protection is required. In Windows PowerShell, set `$env:ROBOT_ALLOW_UNLOCALIZED_CONTROL = "0"` before launching.

## Robot and arena configuration {#robot-and-arena-configuration}

Use the console or `GET/PUT /api/config` for arena size, identities, tag IDs, body outlines, control-point/tag offsets and velocity limits. All robots must be disarmed before saving. Saving stops robots and replaces the session.

Hardware saves synchronize robot tag IDs, black-border sizes and mounting heights to vision. Set heading correction in the control server. The compact acrylic candidate uses nominal 72 mm black borders and 80 mm finished labels; V11 uses 104/130 mm. Measure height from the floor to the tag centre. Saved settings do not migrate with hardware changes. Let only one control server manage a shared vision profile.

New robot configurations default to `0.10 m/s` and `0.30 rad/s`. Effective limits are the lower of configuration and device reports; existing databases retain saved values. The approximately 200 × 160 mm body envelope is a conservative initial value. Measure the full outline including wheels, tag board and mounting offsets.

## Ownership and networking {#ownership-and-networking}

Use one `X-Control-ID` for HTTP arming and nonzero commands, and the same value for WebSocket `owner`. Other pages or policies cannot overwrite nonzero motion but may stop a robot. Control IDs provide mutual exclusion only.

The service targets local computers and trusted experiment LANs without account authentication or authenticated UDP. GitHub Pages hosts static documentation only.

## Development mode {#development-mode}

Run all commands from the repository root:

```bash
uv run --python 3.12 --extra test pytest -q
uv run --python 3.12 --extra test pytest sdk/python/tests -q
npm --prefix robot_server/frontend run dev
```

The frontend development server proxies the API to local port 8000. Launch scripts do not rebuild an existing `frontend/dist/index.html`; after editing source, run `npm --prefix robot_server/frontend run build`. Use one backend process and worker; run expensive policies separately.
