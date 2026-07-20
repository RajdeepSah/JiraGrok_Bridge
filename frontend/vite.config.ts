import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev, the SPA runs on :5173 and proxies /api to the FastAPI server on :8000,
// so the browser talks to a single origin and no VITE_* secret is ever needed.
// In production the built files are served by FastAPI itself (same origin).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
});
