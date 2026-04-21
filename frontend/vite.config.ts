import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

const backendPort = process.env.TOOLBOX_BACKEND_PORT ?? '3001'
const frontendPort = Number(process.env.TOOLBOX_FRONTEND_PORT ?? '3000')
const backendOrigin = `http://127.0.0.1:${backendPort}`

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: frontendPort,
    strictPort: true,
    proxy: {
      '/api/v1': {
        target: backendOrigin,
        changeOrigin: true,
      },
      '/static': {
        target: backendOrigin,
        changeOrigin: true,
      },
    },
  },
})
