import { expect, test as base } from '@playwright/test'
import type { Settings } from '../../robot_server/frontend/src/types'

export { expect } from '@playwright/test'

export const test = base.extend<{ resetFleet: void }>({
  resetFleet: [async ({ request, page }, use) => {
    const settings: Settings = {
      vision_url: '', arena_width: 10, arena_height: 10,
      robots: ['#28786b', '#427dc2', '#ac7b35', '#ba6070'].map((color, index) => ({
        id: `car-${String(index+1).padStart(2, '0')}`, name: `小车 ${index+1}`,
        tag_id: 10+index, color, tag_size: .104, tag_height: .0646,
        length: .20, width: .16, body_offset_x: 0, body_offset_y: 0,
        tag_offset_x: 0, tag_offset_y: 0, heading_offset: 0, max_v: .50, max_omega: 1.50,
      })),
    }
    expect((await request.post('/api/stop')).ok()).toBeTruthy()
    expect((await request.put('/api/config', { data: settings })).ok()).toBeTruthy()
    expect((await request.post('/api/reset-stop')).ok()).toBeTruthy()
    await expect.poll(async () => {
      const state = await (await request.get('/api/state')).json()
      return state.robots.every((robot: {online: boolean}) => robot.online)
    }).toBeTruthy()
    try {
      await use()
    } finally {
      await page.close()
      expect((await request.post('/api/stop')).ok()).toBeTruthy()
    }
  }, { auto: true }],
})
