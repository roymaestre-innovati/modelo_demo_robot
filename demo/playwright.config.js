import { defineConfig } from '@playwright/test';

// Usa el Chrome del sistema (channel 'chrome'). Si no lo tienes: `npx playwright install chromium`
// y cambia channel por undefined.
export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  use: {
    baseURL: 'http://localhost:5199',
    channel: process.env.PW_CHANNEL ?? 'chrome',
    viewport: { width: 1280, height: 800 },
    // GPU real en headless; PW_SWIFTSHADER=1 fuerza render por software (lento: ~1-4 FPS)
    launchOptions: {
      args: process.env.PW_SWIFTSHADER
        ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']
        : ['--enable-gpu', '--ignore-gpu-blocklist'],
    },
  },
  webServer: {
    command: 'npm run dev -- --port 5199 --strictPort',
    url: 'http://localhost:5199',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
