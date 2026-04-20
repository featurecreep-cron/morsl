import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8321',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8321',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://localhost:8321',
        changeOrigin: true,
      },
      '/sse': {
        target: 'http://localhost:8321',
        changeOrigin: true,
      },
      '/css': {
        target: 'http://localhost:8321',
        changeOrigin: true,
      },
      '/icons': {
        target: 'http://localhost:8321',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../web',
    emptyOutDir: true,
  },
})
