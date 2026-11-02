# Device protocol and timing

Devices use the explicit-arming revision of UDP JSON `version=1`. Pair the server with this repository's firmware. Historical v1 packets may lack currently required fields; version number 1 alone does not establish compatibility.

## Identity and sessions {#identity-and-sessions}

`robot_id` is persistent; `boot_id` changes on each boot. Telemetry and commands have separate increasing sequence numbers. The server's `session` identifies a control session. Devices accept only commands matching boot, session and sequence rules.

Devices send telemetry at approximately 20 Hz to server UDP port 9999, and the server replies to the source endpoint. Four identities are provided, `car-01` through `car-04`. Do not flash every board with the same identity.

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

Latched faults require correcting the cause and rebooting. Reconnection restores communication, not motion.

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

Reports identity, boot ID, sequence, `device_state`, firmware, `ack_session/ack_seq`, voltage, encoder counts, wheel speeds, limits, fault and stop reason. Unknown measurements are `null` or omitted.

Parsing/state-machine sources are `esp32_software/firmware/include/command_wire.h` and `protocol.h`. Cross-component tests compile the actual parser and feed it server-generated packets.

## Current timing configuration {#current-timing-configuration}

| Stage | Setting | Meaning |
| --- | --- | --- |
| Device motion task | 50 Hz | TTL checks and wheel-speed control |
| Device telemetry | 20 Hz | Device state and feedback |
| Server state stream | 10 Hz | Latest snapshots |
| Suggested policy updates | About 10 Hz | Validate against inference/network measurements |
| Heartbeat timeout | 1 s | Expiry disarms |
| Localization timeout | 200 ms | Expiry invalidates pose |
| Default action TTL | 300 ms | Configurable 100–500 ms |
| Bind/arm retries | 150 ms | Retry with the corresponding sequence |

These are software thresholds and scheduling targets, not measured wireless delay or physical stopping time. Define clock references when measuring end-to-end latency; do not subtract unsynchronized timestamps from different devices.
