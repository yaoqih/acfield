# Device protocol and timing

Devices use the explicit-arming revision of UDP JSON `version=1`. The server performs this handshake automatically for fresh console input or a first nonzero API command. Pair the server with this repository's firmware. Historical v1 packets may lack currently required fields; version number 1 alone does not establish compatibility.

## Identity and sessions {#identity-and-sessions}

`robot_id` is persistent; `boot_id` changes on each boot. Telemetry and commands have separate increasing sequence numbers. The server's `session` identifies a control session. Devices accept only commands matching boot, session and sequence rules.

Devices send telemetry at approximately 40 Hz to server UDP port 9999, and the server replies to the source endpoint. Four identities are provided, `car-01` through `car-04`. Do not flash every board with the same identity.

## State transitions {#state-transitions}

```text
Boot / disconnect
    ↓
unbound ── Fresh telemetry echo + stop ──► disarmed
                                            │
                                   Explicit arm + ACK
                                            ↓
                                          armed
                                            │
                              stop / TTL / link or device fault
                                            ↓
                                    disarmed / fault
```

Latched faults require correcting the cause and rebooting. After reconnection, fresh input can start the arm handshake. Previously submitted motion is cleared.

## Example command {#example-command}

```json
{
  "version": 1,
  "type": "command",
  "action": "drive",
  "session": "server-session",
  "robot_id": "car-01",
  "boot_id": "per-boot-id",
  "telemetry_seq": 42,
  "seq": 8,
  "v": 0.05,
  "omega": 0.0,
  "ttl_ms": 300,
  "stop": false
}
```

- `stop`: both velocities zero and `stop=true`; stop/disarm and optionally bind a new session.
- `arm`: both velocities zero and `stop=true`; explicit arming requires binding, no fault and a fresh telemetry echo.
- `drive`: execute velocities after arming, echoing recent telemetry from the current boot. Zero velocities with `stop=true` stop motion without rearming.

New session binding must echo telemetry no more than 200 ms old and newer than the previous binding boundary. Historical old-session packets cannot rebind. Duplicate commands do not renew motion TTL.

## Telemetry {#telemetry}

Reports identity, boot ID, sequence, `device_state`, firmware, `ack_session/ack_seq`, `applied_seq`, `sampled_at_ms`, `clock_synced`, `clock_uncertainty_ms`, voltage, encoder counts, wheel speeds, limits, fault and stop reason. `ack_seq` means protocol acceptance; `applied_seq` means a control update was processed. Neither proves physical motion. `sampled_at_ms` is telemetry construction time; wheel speeds come from the latest control cycle. Unknown measurements are `null` or omitted.

Parsing/state-machine sources are `esp32_software/firmware/include/command_wire.h` and `protocol.h`. Cross-component tests compile the actual parser and feed it server-generated packets.

The optional `warning` field is advisory and does not change arming or motion. Failed voltage sensor reads or readings outside 7–16 V report `warning="battery_sensor"` and `voltage_v=null`; the next valid reading clears the warning automatically. Invalid readings interrupt the undervoltage timer; valid readings continuously below 10.5 V for 1 s still trigger the latched `fault="battery_low"` protection. See the [fault and warning table](../guide/troubleshooting#fault-codes) for codes, triggers and recovery.

## Clock synchronization and scheduling {#clock-synchronization-and-scheduling}

At startup the server maps local UTC to monotonic time, tries NTP every 300 s by default and slews corrections at at most 1 ms/s without changing the operating-system clock. Offline operation works, but consistent time does not establish accurate UTC. Inspect source and pending correction through `GET /api/time`. TTL, heartbeat and loss checks use monotonic time.

ESP32 over UDP and browsers over WebSocket initiate four-timestamp `time_sync` exchanges every second, preferring low-RTT samples. Devices reject scheduled motion after 15 s without synchronization or estimated uncertainty above 20 ms. The estimate depends on network-path and drift assumptions and is not an accuracy guarantee.

Nonzero `drive` may include `execute_at_ms` in server-mapped Unix milliseconds. The console omits this field. The server supplies +60 ms for synchronized devices and sends immediately for unsynchronized devices. Explicit nonzero execution times must be 15–150 ms ahead of the server clock and require device synchronization. Demo applies immediately. Measure scheduling performance on hardware.

Encoder diagnostics use the HTTP/WS command option `immediate: true` to suppress default scheduling. The firmware receives its existing unscheduled command format and checks TTL using its local monotonic clock. WebSocket-only `hold: true` starts server-side renewal until disconnect, stop or expiry. See the [control API](./api) for supported diagnostic firmware and PWM limits.

Devices map execution time to a monotonic deadline in a bounded queue processed by the 10 ms control task. Packets arriving past execution time, waiting over 150 ms or waiting at least their TTL are rejected. Queued packets more than 20 ms late are discarded, and a full queue drops new packets. TTL starts on reception and includes queue wait; duplicates do not renew it. Accepted zero motion clears future motion, and `stop` also disarms. Fault/loss handling bypasses scheduling.

See [TIMING.md](https://github.com/yaoqih/acfield/blob/main/robot_server/TIMING.md) for design and measurement details. Update the server, frontend and firmware together; `version=1` alone does not establish timing compatibility.

## Current timing configuration {#current-timing-configuration}

| Stage | Setting | Meaning |
| --- | --- | --- |
| Device motion task | 100 Hz | TTL checks and wheel-speed control |
| Device telemetry | 40 Hz | Device state and feedback |
| Server loop and state stream | 40 Hz | 25 ms scheduling target; latest snapshots |
| Console joystick targets | 40 Hz | Ordered WebSocket; skip missed cycles |
| Python velocity example | About 10 Hz | Example rate; validate policies against inference/network measurements |
| Heartbeat timeout | 3 s for normal and diagnostic firmware | Expiry disarms |
| Continuous diagnostic duration | 120 s | Server deadline; PWM changes preserve it |
| Localization timeout | 200 ms | Expiry invalidates pose |
| Default action TTL | 300 ms | Configurable 100–500 ms |
| Bind/arm retries | 150 ms | Retry with the corresponding sequence |

These are software thresholds and scheduling targets, not measured wireless delay or physical stopping time. Define clock references when measuring end-to-end latency; do not subtract unsynchronized timestamps from different devices.
