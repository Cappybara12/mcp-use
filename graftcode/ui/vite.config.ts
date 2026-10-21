import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { readFileSync } from 'node:fs'

// scripts/start.sh writes the generated Graft package name here (it can differ per machine).
const { name: graftPackage } = JSON.parse(
  readFileSync(new URL('./graft-package.json', import.meta.url), 'utf8'),
)

// The browser imports the generated Graft directly and talks to the Graftcode Gateway
// over WebSocket. There is no HTTP adapter in this app.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { 'graft-client': graftPackage } },
  // The generated package uses top-level await, so target modern browsers.
  build: { target: 'esnext' },
  optimizeDeps: { esbuildOptions: { target: 'esnext' } },
  server: { port: 5173 },
})
