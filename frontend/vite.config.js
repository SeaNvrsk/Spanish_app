import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Dev server proxies /api to the FastAPI backend on :8010
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const base = env.VITE_BASE_PATH || '/'
  return {
    base,
    plugins: [
      react(),
      tailwindcss(),
      {
        name: 'ios-safe-html',
        transformIndexHtml(html) {
          // crossorigin on module scripts can block eval on some mobile Safari paths
          // when ACAO headers are missing/stripped.
          return html.replace(/\s+crossorigin(?:="[^"]*")?/g, '')
        },
      },
    ],
    build: {
      modulePreload: false,
      rollupOptions: {
        output: {
          // One classic bundle avoids Safari's fragile module/blob/importmap path.
          // The post-build script transports it in sub-48KiB pieces.
          format: 'iife',
          inlineDynamicImports: true,
          entryFileNames: 'assets/app.js',
        },
      },
      chunkSizeWarningLimit: 1200,
    },
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8010',
          changeOrigin: true,
        },
      },
    },
  }
})
