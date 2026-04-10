import { defineConfig } from 'vitest/config';
import { dirname } from 'path';
import { fileURLToPath } from 'url';

const testDir = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: testDir,
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['frontend/setup.js'],
    include: ['frontend/**/*.test.js'],
    silent: process.env.VITEST_SILENT !== '0'
  }
});
