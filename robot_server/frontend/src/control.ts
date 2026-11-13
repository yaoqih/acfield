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
// Keep travelling corrections gentle; pivots use the vehicle's full yaw limit.
export const joystickArcMaxOmega = 1.5
// Give sideways input a forgiving pivot sector, then blend into travel by 45°.
const pivotSectorAngle = 20*Math.PI/180
const travelSectorAngle = 45*Math.PI/180

export function bodyVelocity(stick: { x: number; y: number }, maxV: number, maxOmega: number,
                             trackWidth = joystickTrackWidth) {
  const magnitude = Math.hypot(stick.x, stick.y)
  if (magnitude === 0) return { v: 0, omega: 0 }
  const arcYawLimit = Math.min(maxOmega, joystickArcMaxOmega)
  // Soften small angular deviations around straight travel. Shape the angle
  // before restoring magnitude so pulling back the stick still scales linearly.
  const lateral = stick.x/magnitude
  const steering = magnitude*(.35*lateral + .65*lateral**3)
  // While travelling, couple steering to throttle. Limit each wheel's speed
  // deviation to 70% of the mean, leaving the inner wheel a same-sign target
  // of at least 30% even with a low linear/high yaw speed configuration.
  // Reverse the arc's yaw when backing up, so left/right selects the path of
  // the moving end of the car (tail in reverse), as with a steering wheel.
  const arcOmega = -steering*(stick.y/magnitude)*Math.min(arcYawLimit, 1.4*maxV/trackWidth)
  // Within 20° of either side, remove travel and use an unsoftened pivot.
  // From 20° to 45°, ease both travel and yaw together: a small hand-angle
  // error should not drop pivot authority or leave the car slowly creeping.
  const fromHorizontal = Math.atan2(Math.abs(stick.y), Math.abs(stick.x))
  const blend = Math.max(0, Math.min(1,
    (fromHorizontal-pivotSectorAngle)/(travelSectorAngle-pivotSectorAngle)))
  const arcWeight = blend*blend*(3-2*blend)
  const v = stick.y*maxV*arcWeight
  const omega = arcWeight*arcOmega+(1-arcWeight)*(-stick.x*maxOmega)
  // Pure horizontal input turns the nose; the blend stays continuous even
  // where a reversing arc transitions into an oppositely directed pivot.
  return { v, omega }
}

export function elapsedMs(monotonicNow: number, receivedAt: number) {
  return Math.max(0, monotonicNow-receivedAt)
}
