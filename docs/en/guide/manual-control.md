# Manual control

The console `/`, phone page `/mobile`, and encoder page `/encoder` share fleet state and ownership. Each robot has one controller at a time.

## Steering response {#steering}

The joystick is relative to the nose. Up drives forward, down reverses, sides pivot, and diagonals trace arcs. Forward-right requests a faster left wheel. Reverse-left guides the tail back-left while the nose turns the opposite way.

| Input region | Response |
| --- | --- |
| Within 45° of forward or reverse | Travelling arc, inner wheel retains at least 30% of mean wheel speed in the same direction |
| Within 20° above or below horizontal | Pivot, zero linear speed |
| Between those regions | Smooth mixture of travel and rotation, passing through zero inner-wheel speed |

Travelling yaw is capped at the smaller of 1.5 rad/s and the effective vehicle limit, with a softer response near straight input. Full horizontal input uses the complete effective yaw limit. Stick magnitude controls speed.

## Starting and stopping {#lifecycle}

Fresh input starts the arm handshake automatically. Release requests a stop. Releasing arrow keys or losing joystick keyboard focus clears held keys. Space outside an input activates global stop.

Page blur or backgrounding alone does not disarm. Touch release and pointer cancellation end input. Stop, disconnect and expiry discard pending actions. Reconnect and global-stop release require fresh input.

## Sending and execution {#timing}

The joystick sends the latest target over an ordered WebSocket every 25 ms with a 300 ms TTL. The browser omits execution time. The server adds a 60 ms lead for synchronized devices and sends immediately otherwise. Demo applies targets immediately. Measure physical latency separately.

Normal firmware defaults to encoder regulation. See [repository defaults](../reference/defaults) for current values and [encoder diagnostics](./troubleshooting#encoder-diagnostics) for sustained PWM testing.
