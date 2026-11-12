// All UI inputs use right-positive x and forward-positive y; no world-frame rotation.
export function stickVector(right: number, forward: number, deadzone = .12) {
  const length = Math.hypot(right, forward)
  if (!Number.isFinite(length) || length <= deadzone) return { x: 0, y: 0 }
  const magnitude = (Math.min(1, length)-deadzone)/(1-deadzone)
  return { x: right/length*magnitude, y: forward/length*magnitude }
}

// Current chassis axle spacing, matching firmware config::trackWidth. This is
// independent of the collision envelope's body width.
const joystickTrackWidth = .122

export function bodyVelocity(stick: { x: number; y: number }, maxV: number, maxOmega: number,
                             trackWidth = joystickTrackWidth) {
  const magnitude = Math.hypot(stick.x, stick.y)
  if (magnitude === 0) return { v: 0, omega: 0 }
  const forward = Math.abs(stick.y)/magnitude
  const v = stick.y*maxV
  // While travelling, couple steering to throttle. Limit each wheel's speed
  // deviation to 70% of the mean, leaving the inner wheel a same-sign target
  // of at least 30% even with a low linear/high yaw speed configuration.
  const arcOmega = -stick.x*forward*Math.min(maxOmega, 1.4*maxV/trackWidth)
  // Blend into a counter-rotating pivot only near the horizontal axis (~14°).
  // The angular blend preserves proportional response at any stick magnitude;
  // it adds no timer, acceleration ramp or input-rate limit.
  const blend = Math.min(1, forward/.25)
  const arcWeight = blend*blend*(3-2*blend)
  const omega = arcWeight*arcOmega+(1-arcWeight)*(-stick.x*maxOmega)
  // Positive yaw is left; rightward input turns the nose right in either gear.
  return { v, omega }
}

export function elapsedMs(monotonicNow: number, receivedAt: number) {
  return Math.max(0, monotonicNow-receivedAt)
}
