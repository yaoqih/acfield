import { expect, test } from '@playwright/test'

test.beforeEach(async ({ request }) => {
  // Leave room for the faster defaults and reset poses between control scenarios.
  const settings = await (await request.get('/api/config')).json()
  settings.arena_width = settings.arena_height = 10
  expect((await request.put('/api/config', { data: settings })).ok()).toBeTruthy()
  expect((await request.post('/api/reset-stop')).ok()).toBeTruthy()
  await expect.poll(async () => {
    const state = await (await request.get('/api/state')).json()
    return state.robots.every((robot: {online: boolean}) => robot.online)
  }).toBeTruthy()
})

test('joystick sends proportional movement and stops on release', async ({ page }) => {
  const commands: {v: number; omega: number}[] = []
  const failures: (number | string)[] = []
  page.on('websocket', ws => {
    ws.on('framesent', frame => {
      const message = JSON.parse(String(frame.payload))
      if (message.type === 'control') commands.push(message.command)
    })
    ws.on('framereceived', frame => {
      const message = JSON.parse(String(frame.payload))
      if (message.type === 'control_error') failures.push(message.message)
    })
  })
  page.on('response', response => {
    const request = response.request()
    if (request.method() === 'POST' && request.url().includes('/api/robots/car-01/command')) {
      if (response.ok()) commands.push(request.postDataJSON())
      else failures.push(response.status())
    }
  })
  await page.goto('/')
  await expect.poll(async () => Number((await page.getByTestId('update-age').innerText()).match(/[\d.]+/)?.[0])).toBeLessThan(1500)

  const joystick = page.getByRole('application', { name: '方向摇杆' })
  await expect(joystick).toHaveAttribute('aria-disabled', 'false')
  await joystick.scrollIntoViewIfNeeded()
  const box = (await joystick.boundingBox())!
  const x = box.x + box.width / 2, y = box.y + box.height / 2
  await page.mouse.move(x, y - 20)
  await page.mouse.down()
  await expect.poll(() => commands.some(c => c.v > 0 && c.omega === 0)).toBeTruthy()
  const slow = commands.at(-1)!.v
  await page.mouse.move(x, y - 45)
  await expect.poll(() => commands.some(c => c.v > slow * 1.5 && c.omega === 0)).toBeTruthy()
  await page.mouse.move(x, y + 45)
  await expect.poll(() => commands.some(c => c.v < 0 && c.omega === 0)).toBeTruthy()
  commands.length = 0
  await page.mouse.move(x + 40, y - 40)
  await expect.poll(() => commands.some(c => c.v > 0 && c.omega < 0)).toBeTruthy()
  const diagonal = commands.at(-1)!
  // A 45° right-forward arc turns gently and retains positive wheel targets.
  expect(diagonal.omega/diagonal.v).toBeLessThan(-1)
  expect(diagonal.omega/diagonal.v).toBeGreaterThan(-1.6)
  expect(diagonal.v-diagonal.omega*.061).toBeGreaterThan(0)
  expect(diagonal.v+diagonal.omega*.061).toBeGreaterThan(0)
  commands.length = 0
  await page.mouse.move(x - 40, y + 40)
  await expect.poll(() => commands.some(c => c.v < 0 && c.omega < 0)).toBeTruthy()
  commands.length = 0
  await page.mouse.move(x + 40, y + 40)
  await expect.poll(() => commands.some(c => c.v < 0 && c.omega > 0)).toBeTruthy()
  await page.mouse.up()
  await expect.poll(() => commands.at(-1)?.v === 0 && commands.at(-1)?.omega === 0).toBeTruthy()
  const released = commands.length
  await page.waitForTimeout(100)
  expect(commands).toHaveLength(released)

  await expect(joystick).toHaveAttribute('aria-disabled', 'false')
  commands.length = 0
  await joystick.focus()
  await page.keyboard.down('ArrowUp')
  await expect.poll(() => commands.some(c => c.v > 0)).toBeTruthy()
  await page.keyboard.down('ArrowRight')
  await expect.poll(() => commands.some(c => c.v > 0 && c.omega < 0)).toBeTruthy()
  await page.keyboard.up('ArrowUp')
  await expect.poll(() => commands.some(c => c.v === 0 && c.omega < 0)).toBeTruthy()
  await page.keyboard.up('ArrowRight')
  await expect.poll(() => commands.at(-1)?.v === 0 && commands.at(-1)?.omega === 0).toBeTruthy()

  await expect(joystick).toHaveAttribute('aria-disabled', 'false')
  commands.length = 0
  await page.keyboard.down('ArrowUp')
  await expect.poll(() => commands.some(c => c.v > 0)).toBeTruthy()
  const lock = page.getByRole('button', { name: '停车', exact: true })
  await lock.focus()
  await expect.poll(() => commands.at(-1)?.v === 0 && commands.at(-1)?.omega === 0).toBeTruthy()
  await page.keyboard.up('ArrowUp')
  await lock.click()
  await expect(page.getByRole('button', { name: '解锁控制' })).toHaveCount(0)
  expect(failures).toEqual([])
})

test('parking clears held input and fresh input starts without unlocking', async ({ page }) => {
  await page.goto('/')

  const joystick = page.getByRole('application', { name: '方向摇杆' })
  await expect(joystick).toHaveAttribute('aria-disabled', 'false')
  await joystick.focus()
  await page.keyboard.down('ArrowUp')
  await expect.poll(async () => (await (await page.request.get('/api/state')).json()).robots[0].target_v).toBeGreaterThan(0)
  await page.getByRole('button', { name: '停车', exact: true }).click()
  await expect(page.getByRole('button', { name: '解锁控制' })).toHaveCount(0)
  await expect(joystick).toHaveAttribute('aria-disabled', 'false')
  await page.keyboard.up('ArrowUp')
  const state = await (await page.request.get('/api/state')).json()
  expect(state.robots[0].armed).toBe(false)
  expect(state.robots[0].target_v).toBe(0)
  await joystick.focus()
  await page.keyboard.down('ArrowUp')
  await expect.poll(async () => (await (await page.request.get('/api/state')).json()).robots[0].target_v).toBeGreaterThan(0)
  await page.keyboard.up('ArrowUp')
})

for (const path of ['/', '/mobile']) {
  test(`full horizontal joystick input requests a pivot at the vehicle yaw limit on ${path}`, async ({ page, request }) => {
    const settings = await (await request.get('/api/config')).json()
    settings.robots[0].max_omega = 6
    expect((await request.put('/api/config', { data: settings })).ok()).toBeTruthy()
    expect((await request.post('/api/reset-stop')).ok()).toBeTruthy()
    if (path === '/mobile') await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(path)
    const joystick = page.getByRole('application', { name: '方向摇杆' })
    await expect(joystick).toHaveAttribute('aria-disabled', 'false')
    await joystick.scrollIntoViewIfNeeded()
    const box = (await joystick.boundingBox())!
    for (const side of [-1, 1]) {
      const x = box.x+box.width*(.5+side*.45), y = box.y+box.height/2
      await page.mouse.move(x, y)
      await page.mouse.down()
      await expect.poll(async () => {
        const robot = (await (await request.get('/api/state')).json()).robots[0]
        return robot.target_v === 0 && Math.abs(robot.target_omega+side*6) < .001
      }).toBeTruthy()
      // Full rotation must remain easy to find with ordinary finger-angle
      // errors. By 30° the input should still turn strongly while easing travel.
      for (const degrees of [-30, -18, 18, 30]) {
        const angle = degrees*Math.PI/180, radius = box.width*.45
        await page.mouse.move(box.x+box.width/2+side*radius*Math.cos(angle), y+radius*Math.sin(angle))
        await expect.poll(async () => {
          const robot = (await (await request.get('/api/state')).json()).robots[0]
          return Math.abs(degrees) < 20
            ? Math.abs(robot.target_v) < .001 && -side*robot.target_omega > 5.6
            : Math.abs(robot.target_v) < .1 && -side*robot.target_omega > 3
        }).toBeTruthy()
      }
      await page.mouse.up()
      await expect.poll(async () => {
        const robot = (await (await request.get('/api/state')).json()).robots[0]
        return robot.target_v === 0 && robot.target_omega === 0
      }).toBeTruthy()
    }
  })

  test(`joystick continues without clock synchronization on ${path}`, async ({ page, request }) => {
    if (path === '/mobile') await page.setViewportSize({ width: 390, height: 844 })
    let deviceSynced = false
    const commands: { v: number; execute_at_ms?: number }[] = []
    await page.routeWebSocket('**/ws', socket => {
      const server = socket.connectToServer()
      socket.onMessage(raw => {
        const message = JSON.parse(String(raw))
        if (message.type === 'time_sync') return
        if (message.type === 'control' && message.command.v) commands.push(message.command)
        server.send(raw)
      })
      server.onMessage(raw => {
        const message = JSON.parse(String(raw))
        if (message.robots) {
          message.mode = 'hardware'
          message.robots[0].clock_synced = deviceSynced
        }
        socket.send(JSON.stringify(message))
      })
    })
    await page.goto(path)
    const joystick = page.getByRole('application', { name: '方向摇杆' })
    await expect(joystick).toHaveAttribute('aria-disabled', 'false')
    await joystick.focus()
    await page.keyboard.down('ArrowUp')
    await expect.poll(async () => (await (await request.get('/api/state')).json()).robots[0].target_v).toBeGreaterThan(0)
    await expect.poll(() => commands.length).toBeGreaterThan(3)
    deviceSynced = true
    await page.waitForTimeout(150)
    deviceSynced = false
    const before = commands.length
    await expect.poll(() => commands.length).toBeGreaterThan(before + 3)
    await expect(joystick).toHaveAttribute('aria-disabled', 'false')
    expect(commands.every(command => command.execute_at_ms === undefined)).toBeTruthy()
    await page.keyboard.up('ArrowUp')
  })

  test(`joystick keeps 40 Hz differential turning while held on ${path}`, async ({ page }) => {
    if (path === '/mobile') await page.setViewportSize({ width: 390, height: 844 })
    await page.addInitScript(() => {
      const recorded = window as typeof window & { controlSamples: { at: number; v: number; omega: number }[] }
      recorded.controlSamples = []
      const send = WebSocket.prototype.send
      WebSocket.prototype.send = function(data) {
        if (typeof data === 'string') {
          const message = JSON.parse(data)
          if (message.type === 'control' && message.command.v > 0)
            recorded.controlSamples.push({ at: performance.now(), v: message.command.v, omega: message.command.omega })
        }
        return send.call(this, data)
      }
    })
    await page.goto(path)

    const joystick = page.getByRole('application', { name: '方向摇杆' })
    await expect(joystick).toHaveAttribute('aria-disabled', 'false')
    await joystick.focus()
    await page.keyboard.down('ArrowUp')
    await page.keyboard.down('ArrowRight')
    await expect.poll(() => page.evaluate(() =>
      (window as typeof window & { controlSamples: unknown[] }).controlSamples.length)).toBeGreaterThan(2)
    await page.evaluate(() => (window as typeof window & { controlSamples: unknown[] }).controlSamples = [])
    await page.waitForTimeout(1000)
    await page.keyboard.up('ArrowUp')
    await page.keyboard.up('ArrowRight')
    const samples = await page.evaluate(() =>
      (window as typeof window & { controlSamples: { at: number; v: number; omega: number }[] }).controlSamples)
    // Measure in the browser so Playwright transport batching cannot hide a
    // reduced cadence. Allow scheduler jitter, while rejecting 30/20 Hz loops.
    expect(samples.length).toBeGreaterThanOrEqual(36)
    const hz = (samples.length-1)*1000/(samples.at(-1)!.at-samples[0].at)
    expect(hz).toBeGreaterThan(35)
    expect(hz).toBeLessThan(45)
    for (const command of samples) {
      const left = command.v-command.omega*.061, right = command.v+command.omega*.061
      expect(left).toBeGreaterThan(right)
      expect(right).toBeGreaterThan(0)
    }
    // Back-right steers the tail right, then back-left steers it left. Verify
    // the commands received by the server on desktop and mobile alike.
    await page.keyboard.down('ArrowDown')
    await page.keyboard.down('ArrowRight')
    await expect.poll(async () => {
      const robot = (await (await page.request.get('/api/state')).json()).robots[0]
      return robot.target_v < 0 && robot.target_omega > 0
    }).toBeTruthy()
    await page.keyboard.up('ArrowRight')
    await page.keyboard.down('ArrowLeft')
    await expect.poll(async () => {
      const robot = (await (await page.request.get('/api/state')).json()).robots[0]
      return robot.target_v < 0 && robot.target_omega < 0
    }).toBeTruthy()
    await page.keyboard.up('ArrowLeft')
    await page.keyboard.up('ArrowDown')
    await page.getByRole('button', { name: '停车', exact: true }).click()
    await expect(page.getByRole('button', { name: '解锁控制' })).toHaveCount(0)
  })
}

test('congested control retires socket, stops and supports fresh control after reconnect', async ({ page }) => {
  await page.addInitScript(() => {
    const send = WebSocket.prototype.send
    let replay: (() => void) | undefined
    WebSocket.prototype.send = function(data) {
      if (typeof data === 'string') {
        const message = JSON.parse(data)
        if (message.type === 'control' && (message.command.v || message.command.omega)) {
          replay = () => { if (this.readyState !== WebSocket.OPEN) window.dispatchEvent(new Event('old-socket-closed')); else send.call(this, JSON.stringify({ ...message, seq: message.seq + 1000 })) }
        }
      }
      return send.call(this, data)
    }
    window.addEventListener('replay-delayed-motion', () => replay?.())
    window.addEventListener('old-socket-closed', () => document.body.dataset.oldSocketClosed = 'true')
  })
  const rejected: string[] = []
  page.on('websocket', ws => ws.on('framereceived', frame => {
    const message = JSON.parse(String(frame.payload))
    if (message.type === 'control_error') rejected.push(message.message)
  }))
  await page.goto('/')

  const joystick = page.getByRole('application', { name: '方向摇杆' })
  await expect(joystick).toHaveAttribute('aria-disabled', 'false')
  await joystick.focus()
  await page.keyboard.down('ArrowUp')
  await expect.poll(async () => (await (await page.request.get('/api/state')).json()).robots[0].target_v).toBeGreaterThan(0)
  await page.evaluate(() => Object.defineProperty(WebSocket.prototype, 'bufferedAmount', { configurable: true, get: () => 8192 }))
  await page.keyboard.up('ArrowUp')
  await expect(page.getByRole('button', { name: '解锁控制' })).toHaveCount(0)
  await expect.poll(async () => (await (await page.request.get('/api/state')).json()).robots[0].armed).toBe(false)
  await page.evaluate(() => window.dispatchEvent(new Event('replay-delayed-motion')))
  await expect(page.locator('body')).toHaveAttribute('data-old-socket-closed', 'true')
  expect(rejected).toEqual([])
  const state = await (await page.request.get('/api/state')).json()
  expect(state.robots[0].armed).toBe(false)
  expect(state.robots[0].target_v).toBe(0)
  await page.evaluate(() => Object.defineProperty(WebSocket.prototype, 'bufferedAmount', { configurable: true, get: () => 0 }))
  await expect(joystick).toHaveAttribute('aria-disabled', 'false')
  await joystick.focus()
  await page.keyboard.down('ArrowUp')
  await expect.poll(async () => (await (await page.request.get('/api/state')).json()).robots[0].target_v).toBeGreaterThan(0)
  await page.keyboard.up('ArrowUp')
})

test('settings keep edits across sections, reveal invalid fields and save locked', async ({ page }) => {
  let writes = 0
  page.on('request', request => {
    if (request.method() === 'PUT' && request.url().endsWith('/api/config')) writes++
  })
  await page.goto('/')
  await page.getByRole('button', { name: '实验配置', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '实验配置', exact: true })
  const nav = dialog.getByRole('navigation', { name: '配置分区' })
  const firstRobot = dialog.locator('.robot-config').first()
  const name = firstRobot.getByLabel('设备名称', { exact: true })
  await name.fill('')
  await firstRobot.locator('summary').click()
  await nav.getByRole('button', { name: '场地', exact: true }).click()
  const width = dialog.getByLabel('宽度 / m', { exact: true })
  await width.fill('3.5')
  const save = dialog.getByRole('button', { name: '保存配置', exact: true })
  await save.click()
  await expect(firstRobot).toHaveAttribute('open', '')
  await expect(name).toBeFocused()
  expect(writes).toBe(0)

  await name.fill('摇杆回归小车')
  await dialog.getByRole('button', { name: '添加小车', exact: true }).click()
  await expect(dialog.locator('.robot-config')).toHaveCount(5)
  await nav.getByRole('button', { name: '场地', exact: true }).click()
  await expect(width).toHaveValue('3.5')
  const saved = page.waitForResponse(response => response.request().method() === 'PUT' && response.url().endsWith('/api/config'))
  await save.click()
  expect((await saved).ok()).toBeTruthy()
  await expect(dialog).toBeHidden()
  const config = await (await page.request.get('/api/config')).json()
  expect(config.arena_width).toBe(3.5)
  expect(config.robots).toHaveLength(5)
  expect(config.robots[0].name).toBe('摇杆回归小车')
  const state = await (await page.request.get('/api/state')).json()
  expect(state.estop).toBeTruthy()
  expect(state.robots.every((robot: {armed: boolean}) => !robot.armed)).toBeTruthy()
})
