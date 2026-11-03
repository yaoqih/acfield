# Controller integration

The shortest integration path is: read state → request and confirm arming → submit joint velocities → monitor state → stop and disarm on exit. There is no policy plugin framework to learn.

Python algorithms should use the [Python SDK](./python-sdk): `Client` handles HTTP and typed responses; `client.control(...)` waits for arming, checks ownership and releases on exit. Install it independently in your algorithm environment without importing backend modules.

## A bounded example {#a-bounded-example}

Start the [demo server](./quickstart), then run from the repository root:

```bash
.venv/bin/python examples/velocity_control.py --duration 2

# Submit two robots' actions in one batch
.venv/bin/python examples/velocity_control.py --robots car-01 car-02 --duration 2
```

The example defaults to 0.05 m/s, 100 ms updates, a 300 ms TTL and at most 30 seconds. It demonstrates velocity integration, not formation control. It checks mode, readiness and arming, then requests stop/disarm on exit. Ctrl+C enters the same cleanup path; forced termination relies on server and device TTL.

Hardware mode is refused unless `--hardware` is explicit after calibration and acceptance. The example does not automatically release global stop or acquire another controller's robots.

## Understand state {#understand-state}

`GET /api/state` returns the arena, robots, events and camera state. Identity is `robots[i].config.id` and pose is `x/y/theta`. Also inspect arming, online status and localization. The runtime API and actual responses define the fields.

`GET /api/health` reports `ready` for all configured robots meeting binding, online and localization prerequisites. This does not mean they are armed or physically accepted.

## Joint actions {#joint-actions}

```http
POST /api/commands
Content-Type: application/json
X-Control-ID: my-controller

{
  "car-01": {"v": 0.05, "omega": 0, "ttl_ms": 300},
  "car-02": {"v": 0.05, "omega": 0, "ttl_ms": 300}
}
```

`v` is m/s and `omega` is rad/s, counterclockwise positive. Arm with the same control ID and wait for `armed=true`. Rejected validation returns 409 without partially dispatching new motion from the batch.

## Replace the controller {#replace-the-controller}

In the example's `run()` loop, compute each robot's `v/omega` from observations while retaining mode checks, state confirmation, timing and cleanup. Run slow inference in a separate process and associate results with observation time and validity.

Goal points, planar velocity vectors and trajectories need an explicit differential-drive tracker. Do not directly treat ideal planar velocities as wheel speeds or continuously renew old actions to bypass inference expiry.

## Additional research requirements {#additional-research-requirements}

The experiment layer defines initialization, episodes, termination, constrained observations/messages and metrics. The platform does not automatically isolate agents from global state. See [research validity](../design/research) and [recording](./recording).
