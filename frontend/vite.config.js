import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // ── REST ──────────────────────────────────────────────────────
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },

      // ── WebSockets ────────────────────────────────────────────────
      // Covers both /ws/voice and /ws/dashboard
      // target must be http:// — Vite upgrades to ws:// automatically
      '/ws': {
        target: 'http://localhost:8000',
        ws: true,
        changeOrigin: true,
      },

      // ── REMOVED: /session → endpoint does not exist in backend
      // ── REMOVED: /dashboard → already covered by /ws proxy above
      //    (/ws/dashboard starts with /ws so it matches the rule above)
    },
  },
})