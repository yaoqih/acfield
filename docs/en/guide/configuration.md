# Configuration

The server defaults to a local listener and demo mode. Hardware mode must be selected explicitly and does not run the built-in simulator.

Use the console's mode selector to switch the current session between simulated data and hardware. Switching stops and locks all robots; hardware still requires device binding and valid live localization. A restart uses `ROBOT_MODE`. On a phone on the same network, open the console's LAN address and use the touch joystick to control the selected robot; releasing it stops the robot.

## Server environment variables {#server-environment-variables}

| Variable | Default | Purpose |
| --- | --- | --- |
| `ROBOT_MODE` | `demo` | `demo` or `hardware` |
| `ROBOT_HOST` | `127.0.0.1` | HTTP bind address |
| `ROBOT_PORT` | `8000` | HTTP port |
| `ROBOT_UDP_HOST` | `127.0.0.1` | Device bind address; often `0.0.0.0` for LAN devices |
| `ROBOT_UDP_PORT` | `9999` | Device UDP port |
| `ROBOT_VISION_URL` | Unset | Explicitly overrides the saved vision service URL |
| `ROBOT_START_VISION` | `1` | Set to `0` to skip starting local vision |
| `ROBOT_VISION_PORT` | `8765` | Local vision service port started by the script |
| `ROBOT_VISION_RUNTIME_CONFIG` | `output/vision-settings.json` | Vision settings file used by the script |
| `ROBOT_DB` | `robot_server/data/config.sqlite3` | Persistent configuration |
| `ROBOT_LOG_DIR` | `runs/` beside the database | Runtime logs |

## Startup addresses and LAN access {#startup-addresses-and-lan-access}

`./run.sh` and `python -m backend.app` print console/API URLs and detected host IPv4 addresses. The default listener is local only. To connect an SDK on another computer, run inside `robot_server/`:

```bash
ROBOT_HOST=0.0.0.0 ./run.sh
```

Pass a printed `LAN / SDK` URL to `Client("http://HOST_IP:8000")`. Addresses come from hostname resolution and the routing table and may include VPN interfaces. Select an address reachable from the client network. Printing an address does not change the listener.

## Camera vision service {#camera-vision-service}

Run `./run.sh` in `robot_server/` to start the control and local vision services together; the script stops its vision process on exit. The camera is disconnected on the first start, and subsequent starts restore its saved connection state. Demo mode can configure a real camera while robot positions remain simulated. Set `ROBOT_VISION_PORT` if the port is in use. To use an independent or remote vision service, set `ROBOT_START_VISION=0` and enter its address in the console.

In the control console, open **Experiment settings → Camera and vision**, read the service profile, refresh devices and select a camera. The two services may run on separate computers: enter an address reachable from the control server, while the camera index belongs to the computer running vision. Capture width and frame rate are requests; check the reported image dimensions and actual frame rate.

Use measured intrinsics for the current camera and resolution. Measure tag side length at the black border and mounting height from the arena floor to the tag centre. Enter the IDs and coordinates of four fixed tags relative to the arena origin. Save and connect the camera, then choose **Calibrate and save** when all configured fixed tags are visible. Switching cameras or editing intrinsics, dimensions or coordinates requires recalibration. Verify the saved world calibration after restarting.

Vision configuration is stored in the repository root at `output/vision-settings.json`; control settings are stored in `robot_server/data/config.sqlite3`. `apriltag_live.json` remains a source of initial defaults and is not overwritten by runtime edits. Back up physical intrinsics and measured tag coordinates.

## Hardware-mode example {#hardware-mode-example}

After hardware and camera calibration, run inside `robot_server/`:

```bash
ROBOT_MODE=hardware ROBOT_UDP_HOST=0.0.0.0 ./run.sh
```

The default vision address is `http://127.0.0.1:8765`. The console saves the vision service address; setting `ROBOT_VISION_URL` explicitly overrides it at startup.

## Robot and arena configuration {#robot-and-arena-configuration}

Use the console or `GET/PUT /api/config`. Settings include arena size, identities, tag IDs, body outlines, control-point/tag offsets and velocity limits. All robots must be disarmed before saving. A save stops robots and replaces the control session.

On hardware-mode saves, the console synchronizes each robot's AprilTag ID, black-border size and mounting height to the vision service. Set heading correction in the control console. The compact acrylic candidate uses a nominal 72 mm black square and 80 mm finished label; older V11 uses 104/130 mm. Existing defaults do not change automatically with the hardware. Measure mounting height from the arena floor to the tag centre. Ensure only one control service manages shared vision configuration during an experiment.

The default body envelope is approximately 200 × 160 mm, a conservative initial value rather than a measured V11 outline. Include wheels, the tag and mounting offsets when measuring the full envelope.

## Ownership and networking {#ownership-and-networking}

Use the same `X-Control-ID` for arming and nonzero commands. It provides exclusive control, not identity authentication. Another page or policy cannot override a robot's nonzero motion but may request a stop.

The initial system targets a local computer or trusted experiment LAN, with no account authentication or authenticated UDP transport. GitHub Pages serves static documentation only; it does not host the control server or control laboratory robots.

## Development mode {#development-mode}

```bash
# Backend, inside robot_server/
uv run --python 3.12 --extra test pytest -q

# Frontend, from the repository root
npm --prefix robot_server/frontend run dev
```

The frontend development server proxies the API to local port 8000. Use a single process and worker. Run expensive policies in a separate process.
