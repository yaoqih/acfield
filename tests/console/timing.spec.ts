import { expect, test } from '@playwright/test'
import { bodyVelocity, elapsedMs, stickVector } from '../../robot_server/frontend/src/control'
import { ServerClock } from '../../robot_server/frontend/src/timeSync'

test('body-relative joystick keeps signs, proportional diagonals and a continuous deadzone', () => {
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
    if (right && forward) expect(Math.abs(velocity.omega/velocity.v)).toBeCloseTo(3)
  }
  const near = stickVector(.3, .4), far = stickVector(3, 4)
  expect(near.x/near.y).toBeCloseTo(far.x/far.y)
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
