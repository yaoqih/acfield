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

## Hardware-mode example {#hardware-mode-example}

After hardware and camera calibration, run inside `robot_server/`:

```bash
ROBOT_MODE=hardware ROBOT_UDP_HOST=0.0.0.0 ROBOT_VISION_URL=http://127.0.0.1:5050 ./run.sh
```

Running control and vision on the same computer simplifies initial integration. `5050` is the vision default; use the actual configured address.

## Robot and arena configuration {#robot-and-arena-configuration}

Use the console or `GET/PUT /api/config`. Settings include arena size, identities, tag IDs, body outlines, control-point/tag offsets and velocity limits. All robots must be disarmed before saving. A save stops robots and replaces the control session.

The server's `tag_size` is recorded metadata and does not update vision configuration. Set real tag sizes, mounting heights and heading corrections in `apriltag_live.json` and check that the modules agree. The reference uses a 104 mm black square and a 130 mm full-cover label including the white margin. Use size_m=0.104 in vision and record tag_size=0.104 in the server. Nominal height_m=0.0646 must be updated from the installed measurement. Historical or synthetic-demo dimensions are not physical defaults.

The default body envelope is approximately 200 × 160 mm, a conservative initial value rather than a measured V11 outline. Include wheels, the tag and mounting offsets when measuring the full envelope.

## Ownership and networking {#ownership-and-networking}

Use the same `X-Control-ID` for arming and nonzero commands. It provides exclusive control, not identity authentication. Another page or policy cannot override a robot's nonzero motion but may request a stop.

The initial system targets a local computer or trusted experiment LAN, with no account authentication or authenticated UDP transport. GitHub Pages serves static documentation only; it does not host the control server or control laboratory robots.

## Development mode {#development-mode}

```bash
# Backend, inside robot_server/
uv run --extra test pytest -q

# Frontend, from the repository root
npm --prefix robot_server/frontend run dev
```

The frontend development server proxies the API to local port 8000. Use a single process and worker. Run expensive policies in a separate process.
