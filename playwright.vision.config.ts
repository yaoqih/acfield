import { randomUUID } from 'node:crypto'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { defineConfig, devices } from '@playwright/test'

const runtime = join(tmpdir(), `acfield-vision-test-${randomUUID()}.json`)

export default defineConfig({
  testDir: './tests/vision',
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:18127',
    ...devices['Desktop Chrome'],
    viewport: { width: 1440, height: 1000 },
    trace: 'retain-on-failure',
    launchOptions: {
      // Some macOS test environments cannot create child-process Mach ports.
      args: process.env.PLAYWRIGHT_SINGLE_PROCESS === '1'
        ? ['--single-process', '--no-zygote', '--in-process-gpu'] : [],
    },
  },
  webServer: {
    command: `uv run --python 3.12 python apriltag_live.py --source demo --backend opencv --port 18127 --runtime-config '${runtime.replaceAll("'", "'\\''")}'`,
    url: 'http://127.0.0.1:18127/api/state',
    reuseExistingServer: false,
  },
})
