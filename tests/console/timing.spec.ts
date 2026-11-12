import { expect, test } from '@playwright/test'
import { bodyVelocity, elapsedMs, stickVector } from '../../robot_server/frontend/src/control'
import { ServerClock } from '../../robot_server/frontend/src/timeSync'

test('body-relative joystick keeps signs, differential arcs and a continuous deadzone', () => {
  expect(stickVector(0, .12)).toEqual({ x: 0, y: 0 })
  expect(stickVector(0, .120001).y).toBeLessThan(.00001)
  for (const right of [-1, 0, 1]) for (const forward of [-1, 0, 1]) {
    const vector = stickVector(right, forward)
    const velocity = bodyVelocity(vector, .1, .3)
    expect(Math.sign(velocity.v)).toBe(Math.sign(forward))
    // JS distinguishes -0; compare direction only for nonzero yaw.
    if (right) expect(Math.sign(velocity.omega)).toBe(-Math.sign(right))
    else expect(velocity.omega === 0).toBe(true)
    expect(Math.hypot(vector.x, vector.y)).toBeLessThanOrEqual(1.0000001)
    if (right && forward) {
      const left = velocity.v-velocity.omega*.122/2
      const rightWheel = velocity.v+velocity.omega*.122/2
      expect(Math.sign(left)).toBe(Math.sign(forward))
      expect(Math.sign(rightWheel)).toBe(Math.sign(forward))
      expect(Math.sign(left-rightWheel)).toBe(Math.sign(right))
    }
  }
  const near = stickVector(.3, .4), far = stickVector(3, 4)
  expect(near.x/near.y).toBeCloseTo(far.x/far.y)
})

test('travelling arcs retain both wheel targets even at low linear and high yaw limits', () => {
  for (const [maxV, maxOmega] of [[.02, 6], [.1, .3], [.5, 1.5], [.89, 3]]) {
    for (let degrees = 15; degrees <= 345; degrees++) {
      const angle = degrees*Math.PI/180
      // The small cone around horizontal deliberately blends into a pivot.
      if (Math.abs(Math.sin(angle)) < .25) continue
      const stick = { x: Math.cos(angle), y: Math.sin(angle) }
      const { v, omega } = bodyVelocity(stick, maxV, maxOmega)
      const left = v-omega*.122/2, right = v+omega*.122/2
      expect(Math.sign(left)).toBe(Math.sign(stick.y))
      expect(Math.sign(right)).toBe(Math.sign(stick.y))
      expect(Math.min(Math.abs(left), Math.abs(right))).toBeGreaterThanOrEqual(.3*Math.abs(v)-1e-10)
      expect(Math.abs(v)).toBeLessThanOrEqual(maxV)
      expect(Math.abs(omega)).toBeLessThanOrEqual(maxOmega)
      if (Math.abs(stick.x) > 1e-10) expect(Math.sign(omega)).toBe(-Math.sign(stick.x))
    }
  }
  // The actual old near-horizontal command reduced the inner target to ~.003
  // m/s. The revised mapping keeps both targets appreciably above zero.
  const oldStick = { x: -1.2145/1.5, y: .0769/.5 }
  const { v, omega } = bodyVelocity(oldStick, .5, 1.5)
  expect(v-omega*.061).toBeGreaterThan(.03)
  expect(v+omega*.061).toBeGreaterThan(.03)
})

test('arc-to-pivot mixing stays continuous, proportional and symmetric', () => {
  expect(bodyVelocity({ x: 1, y: 0 }, .5, 1.5)).toEqual({ v: 0, omega: -1.5 })
  const backward = bodyVelocity({ x: 0, y: -1 }, .5, 1.5)
  expect(backward.v).toBe(-.5)
  expect(backward.omega === 0).toBe(true)
  for (let degrees = 0; degrees < 360; degrees++) {
    const angle = degrees*Math.PI/180
    const stick = { x: Math.cos(angle), y: Math.sin(angle) }
    const full = bodyVelocity(stick, .5, 1.5)
    const half = bodyVelocity({ x: stick.x/2, y: stick.y/2 }, .5, 1.5)
    expect(half.v).toBeCloseTo(full.v/2, 10)
    expect(half.omega).toBeCloseTo(full.omega/2, 10)
    const mirrored = bodyVelocity({ x: -stick.x, y: stick.y }, .5, 1.5)
    expect(mirrored.v).toBeCloseTo(full.v, 10)
    expect(mirrored.omega).toBeCloseTo(-full.omega, 10)
    const reversed = bodyVelocity({ x: stick.x, y: -stick.y }, .5, 1.5)
    expect(reversed.v).toBeCloseTo(-full.v, 10)
    expect(reversed.omega).toBeCloseTo(full.omega, 10)
    const adjacent = bodyVelocity({ x: Math.cos(angle+1e-6), y: Math.sin(angle+1e-6) }, .5, 1.5)
    expect(Math.abs(adjacent.v-full.v)).toBeLessThan(.00001)
    expect(Math.abs(adjacent.omega-full.omega)).toBeLessThan(.0001)
  }
})

test('recent update age uses one monotonic clock independently of epoch time', () => {
  const epoch = 1793933909066
  expect(elapsedMs(1050, 1000)).toBe(50)
  const clock = new ServerClock()
  clock.observe(998, epoch+999, epoch+999, 1000)
  expect(clock.now(1050)).toBeGreaterThan(epoch)
  expect(elapsedMs(1050, 1000)).toBe(50)
  expect(elapsedMs(999, 1000)).toBe(0)
})

test('four timestamps reject bad probes, expire and slew without a wall-clock jump', () => {
  const clock = new ServerClock()
  expect(clock.ready(100)).toBe(false)
  expect(clock.observe(100, 1000102, 1000103, 105)).toBe(true)
  expect(clock.now(105)).toBeCloseTo(1000105)
  expect(clock.ready(105)).toBe(true)
  expect(clock.observe(0, NaN, 0, 1)).toBe(false)
  expect(clock.observe(0, 0, 0, 100)).toBe(false)
  expect(clock.observe(2, 2, 1, 3)).toBe(false)
  expect(clock.observe(2, 2, 2, 1)).toBe(false)
  expect(clock.observe(200, 1000102, 1000103, 205)).toBe(true)
  expect(clock.ready(205)).toBe(false)
  const before = clock.now(205)
  expect(clock.now(1205)-before).toBeCloseTo(999)
  expect(clock.ready(16000)).toBe(false)
})
