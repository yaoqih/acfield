import { expect, test } from '@playwright/test'

for (const path of ['/', '/mobile']) {
  test(`battery sensor warning allows arming and held movement on ${path}`, async ({ page, request }) => {
    if (path === '/mobile') await page.setViewportSize({ width: 390, height: 844 })
    await request.post('/api/stop')
    const settings = await (await request.get('/api/config')).json()
    settings.arena_width = settings.arena_height = 10
    expect((await request.put('/api/config', { data: settings })).ok()).toBeTruthy()
    expect((await request.post('/api/reset-stop')).ok()).toBeTruthy()

    let warning: string | null = 'battery_sensor'
    // Inject the sensor status into the isolated demo server's real state stream.
    await page.routeWebSocket('**/ws', socket => {
      const server = socket.connectToServer()
      server.onMessage(raw => {
        const state = JSON.parse(String(raw))
        if (state.robots) {
          const robot = state.robots.find((r: {config: {id: string}}) => r.config.id === 'car-01')
          robot.warning = warning
          robot.voltage_v = warning ? null : 12.4
          robot.battery = null
        }
        socket.send(JSON.stringify(state))
      })
    })
    await page.goto(path)
    const notice = page.locator('.device-warning')
    await expect(notice).toContainText('不影响运动')

    const joystick = page.getByRole('application', { name: '方向摇杆' })
    await expect(joystick).toHaveAttribute('aria-disabled', 'false')
    await joystick.scrollIntoViewIfNeeded()
    const box = (await joystick.boundingBox())!
    await page.mouse.move(box.x+box.width/2, box.y+box.height/2-30)
    await page.mouse.down()
    try {
      const moving = async () => {
        const state = await (await request.get('/api/state')).json()
        return state.robots[0].armed && state.robots[0].target_v > 0
      }
      await expect.poll(moving).toBeTruthy()
      warning = null
      await expect(notice).toBeHidden()
      await expect(joystick).toHaveAttribute('aria-disabled', 'false')
      await expect.poll(moving).toBeTruthy()
      warning = 'battery_sensor'
      await expect(notice).toBeVisible()
      await expect(joystick).toHaveAttribute('aria-disabled', 'false')
      await expect.poll(moving).toBeTruthy()
    } finally {
      await page.mouse.up()
    }
    await expect.poll(async () => {
      const state = await (await request.get('/api/state')).json()
      return state.robots[0].target_v
    }).toBe(0)
  })
}
