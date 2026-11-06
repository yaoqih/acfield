// All UI inputs use right-positive x and forward-positive y; no world-frame rotation.
export function stickVector(right: number, forward: number, deadzone = .12) {
  const length = Math.hypot(right, forward)
  if (!Number.isFinite(length) || length <= deadzone) return { x: 0, y: 0 }
  const magnitude = (Math.min(1, length)-deadzone)/(1-deadzone)
  return { x: right/length*magnitude, y: forward/length*magnitude }
}

export function bodyVelocity(stick: { x: number; y: number }, maxV: number, maxOmega: number) {
  // Positive yaw is left: pushing right must produce negative omega, in forward and reverse.
  return { v: stick.y*maxV, omega: -stick.x*maxOmega }
}

export function elapsedMs(monotonicNow: number, receivedAt: number) {
  return Math.max(0, monotonicNow-receivedAt)
}
