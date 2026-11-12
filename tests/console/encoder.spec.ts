import { expect, test } from '@playwright/test'

test.beforeEach(async ({ request }) => {
  await request.post('/api/stop')
  const settings = await (await request.get('/api/config')).json()
  settings.arena_width = settings.arena_height = 10
  expect((await request.put('/api/config', { data: settings })).ok()).toBeTruthy()
  expect((await request.post('/api/reset-stop')).ok()).toBeTruthy()
})

test('plots encoder samples and breaks the trace when telemetry disappears', async ({ page }) => {
  let counter = 0
  let available = true
  await page.routeWebSocket('**/ws', socket => {
    const server = socket.connectToServer()
    server.onMessage(raw => {
      const message = JSON.parse(String(raw))
      if (message.robots) {
        const robot = message.robots.find((r: {config: {id: string}}) => r.config.id === 'car-01')
        robot.encoder_left = available ? counter++ : null
        robot.encoder_right = available ? -counter : null
      }
      socket.send(JSON.stringify(message))
    })
  })
  await page.goto('/encoder')
  await expect(page.getByRole('heading', { name: '编码器排查' })).toBeVisible()
  await expect.poll(async () => (await page.getByTestId('line-left').getAttribute('d'))?.includes('L')).toBeTruthy()
  await expect(page.getByTestId('encoder-left')).not.toHaveText('—')
  available = false
  await expect(page.getByTestId('encoder-left')).toHaveText('—')
  await page.waitForTimeout(100)
  available = true
  await expect.poll(async () => ((await page.getByTestId('line-left').getAttribute('d'))?.match(/M/g) ?? []).length).toBeGreaterThan(1)
  await page.getByRole('button', { name: '清空曲线' }).click()
  await expect.poll(async () => ((await page.getByTestId('line-left').getAttribute('d'))?.match(/M/g) ?? []).length).toBe(1)
})

test('drives directly, keeps running on blur and stops on vehicle change', async ({ page, request }) => {
  const ttls: number[] = []
  page.on('websocket', ws => ws.on('framesent', frame => {
    const message = JSON.parse(String(frame.payload))
    if (message.type === 'control' && message.command.v) ttls.push(message.command.ttl_ms)
  }))
  await page.goto('/encoder')
  const forward = page.getByRole('button', { name: '开始前进' })
  const robot = async () => (await (await request.get('/api/state')).json()).robots[0]
  await expect(forward).toBeEnabled()

  await expect(forward).toBeEnabled()
  await forward.click()
  await expect.poll(async () => (await robot()).target_v).toBeGreaterThan(0)
  expect(ttls).toContain(500)
  await page.getByRole('button', { name: '停车' }).click()
  await expect.poll(async () => [(await robot()).target_v, (await robot()).armed]).toEqual([0, false])
  await expect(forward).toBeEnabled()

  await expect(forward).toBeEnabled()
  await forward.click()
  await expect.poll(async () => (await robot()).target_v).toBeGreaterThan(0)
  await page.evaluate(() => {
    window.dispatchEvent(new Event('blur'))
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await page.waitForTimeout(650)
  expect((await robot()).armed).toBeTruthy()
  expect((await robot()).target_v).toBeGreaterThan(0)
  await page.getByLabel('选择小车').selectOption('car-02')
  await expect.poll(async () => [(await robot()).target_v, (await robot()).armed]).toEqual([0, false])
  await expect(forward).toBeEnabled()
})

test('releases control when the socket is congested and rejects delayed motion', async ({ page, request }) => {
  await page.addInitScript(() => {
    const send = WebSocket.prototype.send
    let replay: (() => void) | undefined
    WebSocket.prototype.send = function(data) {
      if (typeof data === 'string') {
        const message = JSON.parse(data)
        if (message.type === 'control' && message.command.v) replay = () => { if (this.readyState !== WebSocket.OPEN) window.dispatchEvent(new Event('old-socket-closed')); else send.call(this, JSON.stringify({ ...message, seq: message.seq + 1000 })) }
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
  await page.goto('/encoder')

  const forward = page.getByRole('button', { name: '开始前进' })
  await expect(forward).toBeEnabled()
  await forward.click()
  await expect.poll(async () => (await (await request.get('/api/state')).json()).robots[0].target_v).toBeGreaterThan(0)
  await page.evaluate(() => Object.defineProperty(WebSocket.prototype, 'bufferedAmount', { configurable: true, get: () => 8192 }))
  await expect.poll(async () => {
    const robot = (await (await request.get('/api/state')).json()).robots[0]
    return [robot.target_v, robot.armed]
  }).toEqual([0, false])
  await page.evaluate(() => window.dispatchEvent(new Event('replay-delayed-motion')))
  await expect(page.locator('body')).toHaveAttribute('data-old-socket-closed', 'true')
  expect(rejected).toEqual([])
})

test('does not take control from another page', async ({ page, request }) => {
  expect((await request.post('/api/robots/car-01/arm', { headers: { 'X-Control-ID': 'another-controller' }, data: { enabled: true } })).ok()).toBeTruthy()
  await page.goto('/encoder')
  await expect(page.getByRole('status')).toContainText('另一页面正在控制此车')
  await expect(page.getByRole('button', { name: '开始前进' })).toBeDisabled()
  await page.getByRole('button', { name: '停车' }).click()
  expect((await (await request.get('/api/state')).json()).robots[0].armed).toBeTruthy()
})

test('normal firmware keeps running when device and browser clocks are unavailable', async ({ page, request }) => {
  let synced = false
  const controls: {v: number; execute_at_ms?: number}[] = []
  await page.routeWebSocket('**/ws', socket => {
    const server = socket.connectToServer()
    socket.onMessage(raw => {
      const message = JSON.parse(String(raw))
      if (message.type === 'time_sync') return
      if (message.type === 'control' && message.command.v) controls.push(message.command)
      server.send(raw)
    })
    server.onMessage(raw => {
      const message = JSON.parse(String(raw))
      if (message.robots) {
        message.mode = 'hardware'
        message.robots[0].clock_synced = synced
      }
      socket.send(JSON.stringify(message))
    })
  })
  await page.goto('/encoder')
  const forward = page.getByRole('button', { name: '开始前进' })
  await expect(forward).toBeEnabled()
  await forward.click()
  await expect.poll(async () => (await (await request.get('/api/state')).json()).robots[0].target_v).toBeGreaterThan(0)
  synced = true
  await page.waitForTimeout(150)
  synced = false
  const before = controls.length
  await expect.poll(() => controls.length).toBeGreaterThan(before + 2)
  await expect(page.getByRole('status').filter({ hasText: '电机运行中' })).toBeVisible()
  expect(controls.every(command => command.execute_at_ms === undefined)).toBeTruthy()
  await page.getByRole('button', { name: '停车' }).click()
})

test('adjusts diagnostic PWM during motion without requiring either clock', async ({ page, request }) => {
  let synced = false
  const settings = await (await request.get('/api/config')).json()
  settings.robots[0].max_v = 1
  await request.put('/api/config', { data: settings })
  await request.post('/api/reset-stop')
  const controls: {v: number; immediate?: boolean; hold?: boolean; execute_at_ms?: number}[] = []
  await page.routeWebSocket('**/ws', socket => {
    const server = socket.connectToServer()
    let holdTimer: ReturnType<typeof setInterval> | undefined
    let renewalSeq = 0
    socket.onClose(() => { clearInterval(holdTimer); server.close() })
    socket.onMessage(raw => {
      const message = JSON.parse(String(raw))
      if (message.type === 'time_sync') return // Leave the browser clock uninitialized.
      if (message.type === 'control') {
        controls.push({ ...message.command })
        // The isolated demo device is used to exercise the UI; hardware acceptance
        // and the firmware PWM mapping are verified by the backend/host tests.
        delete message.command.immediate
        delete message.command.hold
        clearInterval(holdTimer)
        const renew = () => server.send(JSON.stringify({ ...message, seq: ++renewalSeq }))
        renew()
        holdTimer = setInterval(renew, 25)
        return
      }
      server.send(JSON.stringify(message))
    })
    server.onMessage(raw => {
      const message = JSON.parse(String(raw))
      if (message.robots) {
        message.mode = 'hardware'
        const robot = message.robots[0]
        robot.firmware = '0.2.4-encoder-diagnostic'
        robot.encoder_diagnostic = { max_pwm: 255, pwm_per_mps: 350 }
        robot.clock_synced = synced
        robot.wheel_left = .123
        robot.wheel_right = -.234
      }
      socket.send(JSON.stringify(message))
    })
  })
  await page.goto('/encoder')
  const output = page.getByLabel('PWM（0–255 / 255）')
  await expect(output).toBeVisible()
  await expect(page.getByTestId('speed-left')).toHaveText('0.123 m/s')
  await expect(page.getByTestId('speed-right')).toHaveText('-0.234 m/s')

  const forward = page.getByRole('button', { name: '开始前进' })
  await expect(forward).toBeEnabled()
  await forward.click()
  const robot = async () => (await (await request.get('/api/state')).json()).robots[0]
  await expect.poll(async () => (await robot()).target_v).toBeCloseTo(18/350)
  await expect(output).toBeEnabled()
  synced = true
  await output.fill('30')
  await page.getByRole('button', { name: '应用输出' }).click()
  await expect.poll(async () => (await robot()).target_v).toBeCloseTo(30/350)
  await expect(page.getByTestId('commanded-pwm')).toContainText('30 / 255')
  synced = false
  await output.fill('256')
  await page.getByRole('button', { name: '应用输出' }).click()
  await expect(page.getByRole('alert')).toContainText('PWM 必须是 0–255 的整数')
  await expect.poll(async () => (await robot()).target_v).toBeCloseTo(30/350)
  expect(controls.length).toBe(2)
  expect(controls.every(command => command.immediate === true && command.hold === true && command.execute_at_ms === undefined)).toBeTruthy()
  await output.fill('255')
  await page.getByRole('button', { name: '应用输出' }).click()
  await expect.poll(async () => (await robot()).target_v).toBeCloseTo(255/350)
  await expect(page.getByTestId('commanded-pwm')).toContainText('255 / 255')
  await output.fill('0')
  await page.getByRole('button', { name: '应用输出' }).click()
  await expect.poll(async () => (await robot()).target_v).toBe(0)
  expect((await robot()).armed).toBeTruthy()
  await page.getByRole('button', { name: '停车' }).click()
  await expect.poll(async () => (await robot()).armed).toBeFalsy()
  await output.fill('10')

  const reverse = page.getByRole('button', { name: '开始后退' })
  await expect(reverse).toBeEnabled()
  await reverse.click()
  await expect.poll(async () => (await robot()).target_v).toBeCloseTo(-10/350)
  await output.fill('20')
  await page.getByRole('button', { name: '应用输出' }).click()
  await expect.poll(async () => (await robot()).target_v).toBeCloseTo(-20/350)
})

test('rejects a speed above the page limit and applies valid changes while running', async ({ page, request }) => {
  await page.goto('/encoder')

  const forward = page.getByRole('button', { name: '开始前进' })
  await expect(forward).toBeEnabled()
  const speed = page.getByLabel('目标速度（m/s）')
  await speed.fill('1')
  await forward.click()
  await expect(page.getByRole('alert')).toContainText('不超过 0.100 m/s')
  const robot = async () => (await (await request.get('/api/state')).json()).robots[0]
  expect((await robot()).target_v).toBe(0)
  await speed.fill('0.025')
  await forward.click()
  await expect.poll(async () => (await robot()).target_v).toBe(.025)
  await speed.fill('0.075')
  await page.getByRole('button', { name: '应用输出' }).click()
  await expect.poll(async () => (await robot()).target_v).toBe(.075)
})
