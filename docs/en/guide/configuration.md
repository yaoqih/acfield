# Configuration

The server defaults to a local listener and demo mode. Hardware mode must be selected explicitly and does not run the built-in simulator.

## Server environment variables {#server-environment-variables}

| Variable | Default | Purpose |
| --- | --- | --- |
| `ROBOT_MODE` | `demo` | `demo` or `hardware` |
| `ROBOT_HOST` | `127.0.0.1` | HTTP bind address |
| `ROBOT_PORT` | `8000` | HTTP port |
| `ROBOT_UDP_HOST` | `127.0.0.1` | Device bind address; often `0.0.0.0` for LAN devices |
| `ROBOT_UDP_PORT` | `9999` | Device UDP port |
| `ROBOT_VISION_URL` | Empty | Calibrated vision service URL |
| `ROBOT_DB` | `robot_server/data/config.sqlite3` | Persistent configuration |
| `ROBOT_LOG_DIR` | `runs/` beside the database | Runtime logs |

## Startup addresses and LAN access {#startup-addresses-and-lan-access}

`./run.sh` and `python -m backend.app` print console/API URLs and detected host IPv4 addresses. The default listener is local only. To connect an SDK on another computer, run inside `robot_server/`:

```bash
ROBOT_HOST=0.0.0.0 ./run.sh
```

Pass a printed `LAN / SDK` URL to `Client("http://HOST_IP:8000")`. Addresses come from hostname resolution and the routing table and may include VPN interfaces. Select an address reachable from the client network. Printing an address does not change the listener.

## Camera vision service {#camera-vision-service}

From the repository root, run `python apriltag_live.py --source demo` to verify the workflow with synthetic tags, or start a physical camera:

```bash
python apriltag_live.py --source 0 --port 8765
```

In the control console, open **Experiment settings → Camera and vision**, read the service profile, refresh devices and select a camera. The two services may run on separate computers: enter an address reachable from the control server, while the camera index belongs to the computer running vision. Capture width and frame rate are requests; check the reported image dimensions and actual frame rate.

Use measured intrinsics for the current camera and resolution. Measure tag side length at the black border and mounting height from the arena floor to the tag centre. Enter the IDs and coordinates of four fixed tags relative to the arena origin. Save and connect the camera, then choose **Calibrate and save** when all configured fixed tags are visible. Switching cameras or editing intrinsics, dimensions or coordinates requires recalibration. After restarting the vision service, reconnect through the console and verify the saved calibration.

Vision configuration is stored in the repository root at `output/vision-settings.json`; control settings are stored in `robot_server/data/config.sqlite3`. `apriltag_live.json` remains a source of initial defaults and is not overwritten by runtime edits. Back up physical intrinsics and measured tag coordinates.

## Hardware-mode example {#hardware-mode-example}

After hardware and camera calibration, run inside `robot_server/`:

```bash
ROBOT_MODE=hardware ROBOT_UDP_HOST=0.0.0.0 ROBOT_VISION_URL=http://127.0.0.1:8765 ./run.sh
```

Start the repository root's `apriltag_live.py` before hardware control. Its default address is `http://127.0.0.1:8765`. The console can also save the vision service address.

## Robot and arena configuration {#robot-and-arena-configuration}

Use the console or `GET/PUT /api/config`. Settings include arena size, identities, tag IDs, body outlines, control-point/tag offsets and velocity limits. All robots must be disarmed before saving. A save stops robots and replaces the control session.

On hardware-mode saves, the console synchronizes each robot's AprilTag ID, black-border size and mounting height to the vision service. Set heading correction in the control console. The reference black border is 104 mm; the full print with the white margin is 130 mm. Measure mounting height from the arena floor to the tag centre. Ensure only one control service manages shared vision configuration during an experiment.

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
