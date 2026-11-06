import { randomUUID } from 'node:crypto'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/console',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:18125', ...devices['Desktop Chrome'] },
  webServer: {
    command: 'uv run --python 3.12 --extra test --directory robot_server python -m backend.app',
    url: 'http://127.0.0.1:18125/api/health',
    reuseExistingServer: false,
    env: {
      ROBOT_MODE: 'demo', ROBOT_HOST: '127.0.0.1', ROBOT_PORT: '18125',
      ROBOT_DB: join(tmpdir(), `acfield-console-test-${randomUUID()}.sqlite3`),
      ROBOT_DEFAULT_VISION_URL: '', ROBOT_VISION_URL: '',
      ROBOT_NTP_SERVER: '',
    },
  },
})
