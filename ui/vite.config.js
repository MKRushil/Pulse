import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()], // ✅ 保留這個，這是 React 運作的核心
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        timeout: 120000, // 🚨 設定 120 秒超時 (您之前的請求跑了 38 秒，預設 30 秒會斷線)
        proxyTimeout: 120000
      }
    }
  }
})