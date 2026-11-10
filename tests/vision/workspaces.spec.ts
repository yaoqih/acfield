import { expect, test as base, type APIRequestContext, type Page } from '@playwright/test'
import { readFile } from 'node:fs/promises'

// Single-process Chromium exits with its last context, so give each test its own browser.
const test = process.env.PLAYWRIGHT_SINGLE_PROCESS === '1' ? base.extend({
  page: async ({ playwright, browserName, launchOptions, baseURL, viewport }, use) => {
    const browser = await playwright[browserName].launch(launchOptions)
    const context = await browser.newContext({ baseURL, viewport })
    await use(await context.newPage())
    await browser.close()
  },
}) : base

async function mockState(page: Page, request: APIRequestContext) {
  const state = await (await request.get('/api/state')).json()
  Object.assign(state, { status: 'running', state_age_ms: 0, frame_age_ms: 10, recording: false })
  let polls = 0
  let offline = false
  await page.route('**/api/state', route => {
    polls++
    if (offline) return route.abort()
    // Changing values force real table updates during keyboard and input checks.
    const frame = structuredClone(state)
    for (const tag of frame.tags) tag.age_ms = polls
    return route.fulfill({ json: frame })
  })
  return { state, polls: () => polls, setOffline: (value: boolean) => { offline = value } }
}

test('real demo renders and workspaces preserve the current session', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('#connection')).toHaveClass(/good/)
  await expect(page.locator('#tag-roster .tag-card')).toHaveCount(8)
  await expect(page.locator('#view-settings')).toBeHidden()
  await page.getByRole('navigation', { name: '工作区' }).getByRole('link', { name: '设备设置' }).click()
  await page.getByRole('navigation', { name: '设置分组' }).getByRole('link', { name: '相机采集', exact: true }).click()
  await page.getByLabel('目标 FPS').fill('45')
  await page.getByRole('navigation', { name: '工作区' }).getByRole('link', { name: '实时观测' }).click()
  await page.goBack()
  await expect(page.getByLabel('目标 FPS')).toHaveValue('45')
  await expect(page.locator('[data-view="settings"]')).toHaveAttribute('aria-current', 'page')
  await page.reload({ waitUntil: 'domcontentloaded' })
  await expect(page.locator('#view-settings')).toBeVisible()
  expect(errors).toEqual([])
})

test('tag search, status filters and keyboard selection survive polling', async ({ page, request }) => {
  const live = await mockState(page, request)
  live.state.tags.find((tag: { id: number }) => tag.id === 11).status = 'lost'
  await page.goto('/#tags', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('#tag-table tr')).toHaveCount(8)
  await page.getByRole('searchbox', { name: '搜索标签' }).fill('11')
  await expect(page.locator('#tag-table tr')).toHaveCount(1)
  const tag = page.locator('#tag-table [data-tag-id="11"]')
  const tagElement = await tag.elementHandle()
  await tag.focus()
  const initialPolls = live.polls()
  await expect.poll(live.polls).toBeGreaterThan(initialPolls + 2)
  await expect(tag).toBeFocused()
  expect(await tag.evaluate((element, original) => element === original, tagElement)).toBe(true)
  await tag.press('Enter')
  await expect(page.locator('#tag-title')).toContainText('ID 11')
  await expect(page.locator('#tag-status')).toHaveText('丢失')
  await page.getByLabel('观测状态').selectOption('visible')
  await expect(page.locator('#table-empty')).toBeVisible()
  await page.getByRole('button', { name: '清除筛选' }).click()
  await page.getByLabel('观测状态').selectOption('missing')
  await expect(page.locator('#tag-table tr')).toHaveCount(1)
  await page.getByLabel('观测状态').selectOption('unseen')
  await expect(page.locator('#table-empty')).toBeVisible()
})

test('roster opens the inspector and settings anchors support direct links', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await page.locator('#tag-roster [data-tag-id="12"]').click()
  await expect(page).toHaveURL(/#tags$/)
  await expect(page.locator('#tag-title')).toContainText('ID 12')
  await expect(page.locator('#inspector')).toBeFocused()
  await page.goto('/#preview-settings', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('#view-settings')).toBeVisible()
  await expect(page.getByRole('heading', { name: '画面预览' })).toBeInViewport()
  await page.reload({ waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('heading', { name: '画面预览' })).toBeInViewport()
})

test('settings submit confirmed values and prevent duplicate requests', async ({ page, request }) => {
  const live = await mockState(page, request)
  let previewPayload: unknown
  let submissions = 0
  let release = () => {}
  const pending = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/preview', async route => {
    if (route.request().method() === 'GET') return route.fulfill({ json: { width: 960, fps: 25 } })
    submissions++
    previewPayload = route.request().postDataJSON()
    await pending
    await route.fulfill({ json: previewPayload })
  })
  let detectorPayload: unknown
  await page.route('**/api/control', route => {
    detectorPayload = route.request().postDataJSON()
    return route.fulfill({ status: 202, json: { queued: true } })
  })
  await page.goto('/#preview-settings', { waitUntil: 'domcontentloaded' })
  await expect(page.getByLabel('预览 FPS')).toHaveValue('25')
  await page.getByLabel('预览宽度').selectOption('1280')
  await page.getByLabel('预览 FPS').fill('45')
  await expect(page.locator('#preview-form .form-status')).toHaveText('有未应用的修改')
  const submit = page.getByRole('button', { name: '应用预览设置' })
  await submit.click()
  await expect(submit).toBeDisabled()
  await expect(submit).toHaveAttribute('aria-busy', 'true')
  expect(submissions).toBe(1)
  release()
  await expect(submit).toBeEnabled()
  await expect(page.locator('#preview-form .form-status')).toHaveText('与当前设置一致')
  expect(previewPayload).toEqual({ width: 1280, fps: 45 })
  await page.getByRole('link', { name: '标签检测', exact: true }).click()
  await page.getByLabel('检测降采样').selectOption('2')
  const detector = page.getByRole('button', { name: '应用检测参数' })
  await detector.click()
  await expect(detector).toBeDisabled()
  await expect(page.locator('#detector-form .form-status')).toContainText('等待执行结果')
  expect(detectorPayload).toEqual({ action: 'detector', family: 'tag36h11', decimate: 2 })
  live.state.decimate = 2
  live.state.events.unshift({ time: '12:34:56', text: '检测器：tag36h11，降采样 2×', level: 'info' })
  await expect(detector).toBeEnabled()
  await expect(page.locator('#detector-form .form-status')).toHaveText('与当前设置一致')
})

test('queued source failures retain the draft and device changes wait for each other', async ({ page, request }) => {
  const live = await mockState(page, request)
  const submissions: unknown[] = []
  await page.route('**/api/control', route => {
    submissions.push(route.request().postDataJSON())
    return route.fulfill({ status: 202, json: { queued: true } })
  })
  await page.goto('/#source-settings', { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('button', { name: '连接输入源' })).toBeEnabled()
  await page.getByLabel('画面来源').selectOption('2')
  await page.getByRole('button', { name: '连接输入源' }).click()
  await expect(page.locator('#source-form .form-status')).toContainText('等待执行结果')
  await page.getByRole('link', { name: '标签检测', exact: true }).click()
  await page.getByLabel('检测降采样').selectOption('2')
  await page.getByRole('button', { name: '应用检测参数' }).click()
  await expect(page.locator('#detector-form .form-status')).toContainText('等待当前设备操作完成')
  expect(submissions).toEqual([{ action: 'source', source: '2' }])
  live.state.events.unshift({ time: '12:34:56', text: '无法打开相机 2', level: 'error' })
  await page.getByRole('link', { name: '输入源', exact: true }).click()
  await expect(page.locator('#source-form .form-status')).toHaveText('无法打开相机 2')
  await expect(page.getByLabel('画面来源')).toHaveValue('2')
  await page.getByRole('button', { name: '连接输入源' }).click()
  await expect(page.locator('#source-form .form-status')).toContainText('等待执行结果')
  Object.assign(live.state, { source: '2', source_kind: 'camera', demo: false })
  live.state.events.unshift({ time: '12:34:57', text: '已连接输入源 2', level: 'info' })
  await expect(page.locator('#source-form .form-status')).toHaveText('与当前设置一致')
  await expect(page.getByRole('button', { name: '连接输入源' })).toBeEnabled()
})

test('camera errors are inline and drafts survive live updates', async ({ page, request }) => {
  const live = await mockState(page, request)
  Object.assign(live.state, { source: '2', source_kind: 'camera', demo: false })
  const configuration = await (await request.get('/api/config')).json()
  configuration.state = live.state
  let payload: { source?: string, width?: number } = {}
  await page.route('**/api/config', async route => {
    if (route.request().method() === 'GET') return route.fulfill({ json: configuration })
    payload = route.request().postDataJSON()
    await route.fulfill({ status: 400, json: { error: '测试相机无法打开' } })
  })
  await page.goto('/#camera-settings', { waitUntil: 'domcontentloaded' })
  await expect(page.getByLabel('宽度 · px', { exact: true })).toHaveValue('1920')
  await page.getByLabel('宽度 · px', { exact: true }).fill('1280')
  const before = live.polls()
  await expect.poll(live.polls).toBeGreaterThan(before + 2)
  await expect(page.getByLabel('宽度 · px', { exact: true })).toHaveValue('1280')
  await page.getByRole('button', { name: '应用相机设置' }).click()
  await expect(page.locator('#camera-form .form-status')).toHaveText('测试相机无法打开')
  expect(payload).toMatchObject({ source: '2', width: 1280, enabled: true })
  await expect(page.getByRole('button', { name: '应用相机设置' })).toBeEnabled()
  await page.locator('#camera-form').getByRole('button', { name: '恢复当前设置' }).click()
  await expect(page.getByLabel('宽度 · px', { exact: true })).toHaveValue('1920')
  await expect(page.locator('#camera-form .form-status')).toHaveText('与当前设置一致')
})

test('slow configuration loading preserves drafts without blocking preview', async ({ page, request }) => {
  await mockState(page, request)
  const config = await (await request.get('/api/config')).json()
  Object.assign(config.config, { width: 1920, height: 832, fps: 52 })
  let release = () => {}
  const pending = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/config', async route => {
    await pending
    await route.fulfill({ json: config })
  })
  await page.route('**/api/preview', route => route.fulfill({ json: { width: 960, fps: 25 } }))
  await page.goto('/#camera-settings', { waitUntil: 'domcontentloaded' })
  await page.getByLabel('宽度 · px', { exact: true }).fill('1280')
  await page.getByRole('link', { name: '画面预览', exact: true }).click()
  await expect(page.getByLabel('预览 FPS')).toHaveValue('25')
  await page.getByLabel('预览宽度').selectOption('1920')
  await page.getByLabel('预览 FPS').fill('45')
  release()
  await page.getByRole('link', { name: '相机采集', exact: true }).click()
  await expect(page.getByLabel('高度 · px', { exact: true })).toHaveValue('832')
  await expect(page.getByLabel('目标 FPS', { exact: true })).toHaveValue('52')
  await expect(page.getByLabel('宽度 · px', { exact: true })).toHaveValue('1280')
  await page.getByRole('link', { name: '画面预览', exact: true }).click()
  await expect(page.getByLabel('预览宽度')).toHaveValue('1920')
  await expect(page.getByLabel('预览 FPS')).toHaveValue('45')
  await page.locator('#preview-form').getByRole('button', { name: '恢复当前设置' }).click()
  await expect(page.getByLabel('预览宽度')).toHaveValue('960')
  await expect(page.getByLabel('预览 FPS')).toHaveValue('25')
})

test('settings retry a failed read and retain edits', async ({ page, request }) => {
  await mockState(page, request)
  let failed = true
  await page.route('**/api/preview', route => route.fulfill(failed
    ? { status: 503, json: { error: '服务暂不可用' } }
    : { json: { width: 960, fps: 25 } }))
  await page.goto('/#preview-settings', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('#preview-form .form-status')).toContainText('服务暂不可用')
  await expect(page.getByRole('button', { name: '应用预览设置' })).toBeDisabled()
  await page.getByLabel('预览 FPS').fill('45')
  failed = false
  await page.getByRole('button', { name: '重新读取' }).click()
  await expect(page.getByLabel('预览宽度')).toHaveValue('960')
  await expect(page.getByLabel('预览 FPS')).toHaveValue('45')
  await expect(page.getByRole('button', { name: '应用预览设置' })).toBeEnabled()
  await expect(page.locator('#preview-form .form-status')).toHaveText('有未应用的修改')
})

test('mobile tag details open next to the task and restore keyboard focus', async ({ page, request }) => {
  const live = await mockState(page, request)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/#tags', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('#inspector')).toBeHidden()
  const tag = page.locator('#tag-table [data-tag-id="11"]')
  await tag.click()
  await expect(page.getByRole('dialog', { name: '标签检查器' })).toBeVisible()
  await expect(page.locator('#tag-title')).toContainText('ID 11')
  await expect(page.getByRole('button', { name: '关闭标签详情' })).toBeFocused()
  const before = live.polls()
  await expect.poll(live.polls).toBeGreaterThan(before + 2)
  await page.keyboard.press('Escape')
  await expect(page.locator('#tag-dialog')).not.toBeVisible()
  await expect(tag).toBeFocused()
  await expect(page.locator('#inspector')).toBeHidden()
  await tag.press('Enter')
  await page.getByRole('button', { name: '关闭标签详情' }).click()
  await expect(tag).toBeFocused()
  await tag.press('Enter')
  await page.setViewportSize({ width: 1440, height: 1000 })
  await expect(page.locator('#tag-dialog')).not.toBeVisible()
  await expect(page.locator('#inspector-host #inspector')).toBeVisible()
})

test('diagnostics stay compact and preserve all warning details', async ({ page, request }) => {
  const live = await mockState(page, request)
  Object.assign(live.state, { demo: false, calibrated: false, world_calibrated: false,
    warnings: ['相机内参尚未标定', '标签短边不足 35 px，请调整相机距离'] })
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('#notice')).toContainText('像素坐标')
  await expect(page.locator('#diagnostic-list')).not.toBeVisible()
  await expect(page.locator('#diagnostic-action')).toHaveAttribute('href', '/calibration')
  await page.getByText('查看诊断', { exact: false }).click()
  await expect(page.locator('#diagnostic-list li')).toHaveText(live.state.warnings)
  const before = live.polls()
  await expect.poll(live.polls).toBeGreaterThan(before + 2)
  await expect(page.locator('#diagnostic-details')).toHaveAttribute('open')
})

test('a stalled state request expires and polling recovers', async ({ page, request }) => {
  const live = await mockState(page, request)
  await page.goto('/#tags', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('#connection')).toHaveClass(/good/)
  let release = () => {}
  const pending = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/state', async route => {
    await pending
    await route.fulfill({ json: live.state }).catch(() => {})
  })
  await expect(page.locator('#connection')).toHaveText('服务已断开')
  await expect(page.locator('#tag-status')).toHaveText('丢失')
  await page.unroute('**/api/state')
  release()
  await expect(page.locator('#connection')).toHaveClass(/good/)
})

test('stale acquisition marks observations lost even when processing status is running', async ({ page, request }) => {
  const live = await mockState(page, request)
  live.state.frame_age_ms = 1000
  await page.goto('/#tags', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('#connection')).toHaveText('等待输入源')
  await expect(page.locator('#tag-status')).toHaveText('丢失')
  live.state.frame_age_ms = 10
  await expect(page.locator('#connection')).toHaveClass(/good/)
  await expect(page.locator('#tag-status')).toHaveText('可见')
})

test('clearing requires confirmation and Escape cancels without a request', async ({ page, request }) => {
  await mockState(page, request)
  const operations: unknown[] = []
  await page.route('**/api/operations', route => {
    operations.push(route.request().postDataJSON())
    return route.fulfill({ json: {} })
  })
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await page.getByText('场地操作', { exact: true }).click()
  const reset = page.getByRole('button', { name: '清除场地标定', exact: true })
  await reset.click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByRole('button', { name: '取消', exact: true })).toBeFocused()
  expect(operations).toEqual([])
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toBeHidden()
  await expect(reset).toBeFocused()
  await reset.click()
  await page.getByRole('button', { name: '确认清除标定' }).click()
  await expect.poll(() => operations.length).toBe(1)
  expect(operations).toEqual([{ action: 'reset_world' }])
})

test('recording stays visible across views and the toggle waits for state', async ({ page, request }) => {
  const live = await mockState(page, request)
  let calls = 0
  await page.route('**/api/control', async route => {
    calls++
    expect(route.request().postDataJSON()).toEqual({ action: 'record' })
    await route.fulfill({ status: 202, json: { queued: true } })
  })
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '开始记录' }).click()
  await expect(page.locator('#record')).toBeDisabled()
  live.state.recording = true
  live.state.record_path = 'output/live/test/frames.jsonl'
  await expect(page.getByRole('button', { name: '停止记录' })).toBeEnabled()
  await page.locator('[data-view="settings"]').click()
  await expect(page.getByRole('button', { name: '停止记录' })).toHaveAttribute('aria-pressed', 'true')
  expect(calls).toBe(1)
})

test('disconnect marks retained observations as lost and recovers', async ({ page, request }) => {
  const live = await mockState(page, request)
  await page.goto('/#tags', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('#tag-status')).toHaveText('可见')
  live.setOffline(true)
  await expect(page.locator('#connection')).toHaveText('服务已断开')
  await expect(page.locator('#tag-status')).toHaveText('丢失')
  await expect(page.locator('#notice')).toContainText('无法连接本地识别服务')
  await expect(page.locator('#tag-table tr.selected')).not.toContainText('m/s')
  live.setOffline(false)
  await expect(page.locator('#connection')).toHaveClass(/good/)
  await expect(page.locator('#tag-status')).toHaveText('可见')
})

test('export menu dismisses and JSON download contains actual observations', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  const summary = page.locator('#export-menu summary')
  await summary.click()
  await page.keyboard.press('Escape')
  await expect(page.locator('#export-menu')).not.toHaveAttribute('open')
  await expect(summary).toBeFocused()
  await summary.click()
  await page.locator('#workspace-title').click()
  await expect(page.locator('#export-menu')).not.toHaveAttribute('open')
  await summary.click()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('link', { name: '完整观测状态' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('apriltag_state.json')
  expect(await download.failure()).toBeNull()
  const state = JSON.parse(await readFile((await download.path())!, 'utf8'))
  expect(state).toMatchObject({ source: 'demo', demo: true })
  expect(state.tags).toHaveLength(8)
  expect(state.tags[0].center_px).toHaveLength(2)
})

for (const width of [390, 768, 1440]) {
  test(`workspaces and calibration fit a ${width}px screen`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 })
    await page.goto('/', { waitUntil: 'domcontentloaded' })
    await expect(page.locator('#connection')).toHaveClass(/good/)
    for (const view of ['observe', 'tags', 'settings']) {
      await page.locator(`[data-view="${view}"]`).click()
      await expect(page.locator(`#view-${view}`)).toBeVisible()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await expect(page.locator('#record')).toBeInViewport()
    }
    await page.goto('/calibration', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('button', { name: '采集当前画面' })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await expect(page.getByRole('link', { name: '返回观测台' })).toHaveAttribute('href', '/')
  })
}
