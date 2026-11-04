import { expect, test } from '@playwright/test'

test('joystick sends proportional movement and stops on release', async ({ page }) => {
  const commands: {v: number; omega: number}[] = []
  const failures: number[] = []
  page.on('response', response => {
    const request = response.request()
    if (request.method() === 'POST' && request.url().includes('/api/robots/car-01/command')) {
      if (response.ok()) commands.push(request.postDataJSON())
      else failures.push(response.status())
    }
  })
  await page.goto('/')
  const arm = page.getByRole('button', { name: '解锁控制' })
  await expect(arm).toBeEnabled()
  await arm.click()
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
  await page.mouse.up()
  await expect.poll(() => commands.at(-1)?.v === 0 && commands.at(-1)?.omega === 0).toBeTruthy()

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
  const lock = page.getByRole('button', { name: '锁定控制', exact: true })
  await lock.focus()
  await expect.poll(() => commands.at(-1)?.v === 0 && commands.at(-1)?.omega === 0).toBeTruthy()
  await page.keyboard.up('ArrowUp')
  await lock.click()
  await expect(arm).toBeVisible()
  expect(failures).toEqual([])
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
