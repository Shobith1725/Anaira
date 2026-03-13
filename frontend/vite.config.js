import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // ── REST endpoints ─────────────────────────────────────────────
      '/session': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },

      // ── WebSocket: voice pipeline ──────────────────────────────────
      // Backend: @router.websocket("/ws/voice") in voice_pipeline.py
      // NOTE: target must use http:// even for WS — http-proxy upgrades it
      '/ws': {
        target: 'http://localhost:8000',
        ws: true,
        changeOrigin: true,
      },

      // ── WebSocket: dashboard live feed ────────────────────────────
      // Backend: @router.websocket("/dashboard") in dashboard_ws.py
      '/dashboard': {
        target: 'http://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
