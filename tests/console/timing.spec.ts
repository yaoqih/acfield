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
    if (right) expect(Math.sign(velocity.omega)).toBe(-Math.sign(right)*(forward < 0 ? -1 : 1))
    else expect(velocity.omega === 0).toBe(true)
    expect(Math.hypot(vector.x, vector.y)).toBeLessThanOrEqual(1.0000001)
    if (right && forward) {
      const left = velocity.v-velocity.omega*.122/2
      const rightWheel = velocity.v+velocity.omega*.122/2
      expect(Math.sign(left)).toBe(Math.sign(forward))
      expect(Math.sign(rightWheel)).toBe(Math.sign(forward))
      expect(Math.sign(Math.abs(left)-Math.abs(rightWheel))).toBe(Math.sign(right))
      // Integrate the requested arc: its sideways displacement must follow
      // the stick in both gears (body left is positive, stick right positive).
      const sideways = velocity.v*(1-Math.cos(velocity.omega))/velocity.omega
      expect(Math.sign(sideways)).toBe(-Math.sign(right))
    }
  }
  const near = stickVector(.3, .4), far = stickVector(3, 4)
  expect(near.x/near.y).toBeCloseTo(far.x/far.y)
})

test('travelling arcs retain both wheel targets even at low linear and high yaw limits', () => {
  for (const [maxV, maxOmega] of [[.02, 6], [.1, .3], [.5, 1.5], [.5, 6], [.89, 3]]) {
    for (let degrees = 15; degrees <= 345; degrees++) {
      const angle = degrees*Math.PI/180
      // Forward/back sectors retain same-direction wheel targets; the side
      // sectors deliberately blend into counter-rotating pivots.
      if (Math.abs(Math.sin(angle)) < Math.abs(Math.cos(angle))-1e-10) continue
      const stick = { x: Math.cos(angle), y: Math.sin(angle) }
      const { v, omega } = bodyVelocity(stick, maxV, maxOmega)
      const left = v-omega*.122/2, right = v+omega*.122/2
      expect(Math.sign(left)).toBe(Math.sign(stick.y))
      expect(Math.sign(right)).toBe(Math.sign(stick.y))
      expect(Math.min(Math.abs(left), Math.abs(right))).toBeGreaterThanOrEqual(.3*Math.abs(v)-1e-10)
      expect(Math.abs(v)).toBeLessThanOrEqual(maxV)
      expect(Math.abs(omega)).toBeLessThanOrEqual(maxOmega)
      if (Math.abs(stick.x) > 1e-10) expect(Math.sign(omega)).toBe(-Math.sign(stick.x*stick.y))
    }
  }
  // An old near-horizontal command left one wheel almost stopped. It now
  // requests a clear pivot throughout the forgiving side sector.
  const oldStick = { x: -1.2145/1.5, y: .0769/.5 }
  const { v, omega } = bodyVelocity(oldStick, .5, 1.5)
  expect(v).toBe(0)
  expect(v-omega*.061).toBeLessThan(-.07)
  expect(v+omega*.061).toBeGreaterThan(.07)
})

test('arc-to-pivot mixing stays continuous, proportional and symmetric', () => {
  expect(bodyVelocity({ x: 1, y: 0 }, .5, 1.5)).toEqual({ v: 0, omega: -1.5 })
  const backward = bodyVelocity({ x: 0, y: -1 }, .5, 1.5)
  expect(backward.v).toBe(-.5)
  expect(backward.omega === 0).toBe(true)
  for (const yawLimit of [.3, 1.5, 6]) for (let degrees = 0; degrees < 360; degrees++) {
    const angle = degrees*Math.PI/180
    const stick = { x: Math.cos(angle), y: Math.sin(angle) }
    const full = bodyVelocity(stick, .5, yawLimit)
    const half = bodyVelocity({ x: stick.x/2, y: stick.y/2 }, .5, yawLimit)
    expect(half.v).toBeCloseTo(full.v/2, 10)
    expect(half.omega).toBeCloseTo(full.omega/2, 10)
    const mirrored = bodyVelocity({ x: -stick.x, y: stick.y }, .5, yawLimit)
    expect(mirrored.v).toBeCloseTo(full.v, 10)
    expect(mirrored.omega).toBeCloseTo(-full.omega, 10)
    const reversed = bodyVelocity({ x: stick.x, y: -stick.y }, .5, yawLimit)
    expect(reversed.v).toBeCloseTo(-full.v, 10)
    // Forward/reverse arcs trace mirrored paths. Near horizontal, both blend
    // continuously into the same nose-directed pivot instead of flipping it.
    if (Math.abs(stick.y) >= Math.abs(stick.x)) expect(reversed.omega).toBeCloseTo(-full.omega, 10)
    if (stick.y === 0) expect(reversed.omega).toBeCloseTo(full.omega, 10)
    const adjacent = bodyVelocity({ x: Math.cos(angle+1e-6), y: Math.sin(angle+1e-6) }, .5, yawLimit)
    expect(Math.abs(adjacent.v-full.v)).toBeLessThan(.00001)
    expect(Math.abs(adjacent.omega-full.omega)).toBeLessThan(.0001)
  }
})

test('small steering corrections stay gentle even with a high vehicle yaw limit', () => {
  const angle = 5*Math.PI/180
  for (const direction of [-1, 1]) for (const side of [-1, 1]) {
    const stick = { x: side*Math.sin(angle), y: direction*Math.cos(angle) }
    const { v, omega } = bodyVelocity(stick, .5, 6)
    expect(v).toBeCloseTo(direction*.4981, 4)
    // A 5° hand deviation should request less than 3°/s, previously ~29°/s.
    expect(Math.abs(omega)).toBeLessThan(.05)
    expect(Math.abs(omega)).toBeGreaterThan(.04)
    expect(Math.sign(omega)).toBe(-side*direction)
    const half = bodyVelocity({ x: stick.x/2, y: stick.y/2 }, .5, 6)
    expect(half.omega).toBeCloseTo(omega/2, 10)
  }
  let previous = 0
  for (const degrees of [5, 10, 20, 45]) {
    const angle = degrees*Math.PI/180
    const { omega } = bodyVelocity({ x: Math.sin(angle), y: Math.cos(angle) }, .5, 6)
    expect(-omega).toBeGreaterThan(previous)
    previous = -omega
  }
})

test('horizontal input uses full vehicle yaw authority and opposite wheel targets', () => {
  for (const limit of [.3, 1.5, 3, 6]) for (const side of [-1, 1]) {
    for (const magnitude of [.25, .5, 1]) {
      const { v, omega } = bodyVelocity({ x: side*magnitude, y: 0 }, .5, limit)
      expect(v).toBe(0)
      expect(omega).toBeCloseTo(-side*magnitude*limit, 10)
      expect(Math.sign(v-omega*.061)).toBe(side)
      expect(Math.sign(v+omega*.061)).toBe(-side)
    }
    // A small vertical touch error must still leave a strong pivot, including
    // on the reverse side of the arc-to-pivot transition.
    for (const y of [-.02, .02]) {
      const { v, omega } = bodyVelocity(stickVector(side, y), .5, limit)
      expect(Math.abs(v)).toBeLessThan(.011)
      expect(Math.abs(omega)).toBeGreaterThan(.97*limit)
      expect(Math.sign(omega)).toBe(-side)
    }
  }
})

test('side sectors keep strong pivots and ease continuously into travelling arcs', () => {
  for (const side of [-1, 1]) for (const gear of [-1, 1]) {
    for (const degrees of [0, 5, 10, 15, 20]) {
      const angle = degrees*Math.PI/180
      const stick = { x: side*Math.cos(angle), y: gear*Math.sin(angle) }
      const { v, omega } = bodyVelocity(stick, .5, 6)
      expect(Math.abs(v)).toBeLessThan(1e-10)
      expect(-side*omega).toBeGreaterThanOrEqual(5.6)
      const half = bodyVelocity({ x: stick.x/2, y: stick.y/2 }, .5, 6)
      expect(half.omega).toBeCloseTo(omega/2, 10)
    }
    const angle = 30*Math.PI/180
    const midway = bodyVelocity({ x: side*Math.cos(angle), y: gear*Math.sin(angle) }, .5, 6)
    expect(-side*midway.omega).toBeGreaterThan(3)
    expect(Math.sign(midway.v)).toBe(gear)
    expect(Math.abs(midway.v)).toBeLessThan(.1)
    // At both transition boundaries, the response should have no jump or
    // sudden change in slope as a hand sweeps across the sector.
    for (const degrees of [20, 45]) {
      const angle = degrees*Math.PI/180, step = 1e-4
      const at = (a: number) => bodyVelocity({ x: side*Math.cos(a), y: gear*Math.sin(a) }, .5, 6)
      const before = at(angle-step), boundary = at(angle), after = at(angle+step)
      expect(Math.abs(after.omega-boundary.omega)).toBeLessThan(.001)
      expect(Math.abs(boundary.omega-before.omega)).toBeLessThan(.001)
      expect((after.omega-boundary.omega)/step).toBeCloseTo((boundary.omega-before.omega)/step, 1)
      expect((after.v-boundary.v)/step).toBeCloseTo((boundary.v-before.v)/step, 2)
    }
  }
  let previous = 0
  for (let degrees = 0; degrees <= 90; degrees++) {
    const angle = degrees*Math.PI/180
    const { omega } = bodyVelocity({ x: Math.sin(angle), y: Math.cos(angle) }, .5, 6)
    expect(-omega).toBeGreaterThanOrEqual(previous-1e-10)
    previous = -omega
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
