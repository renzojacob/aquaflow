import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from "@tailwindcss/vite";


export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      // lets us write '@/services/http' instead of '../../services/http'
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 8100, // backend CORS already allows this port
    host: true, // also reachable from your phone on the same Wi-Fi
  },
})