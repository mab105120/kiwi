import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.js'],
    coverage: {
      provider: 'v8',
      // TODO: raise to 80% (spec target) once more frontend code/tests land.
      thresholds: {
        statements: 50,
        lines: 50,
      },
    },
  },
})
