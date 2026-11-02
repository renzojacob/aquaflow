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
    strictPort: true,
    host: true, // also reachable from your phone on the same Wi-Fi
    // Phone testing through an https tunnel (Cloudflare): the phone only talks to THIS server,
    // and these requests are passed on to Django. Use VITE_API_BASE_URL=/ to switch it on.
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/admin': { target: 'http://localhost:8000', changeOrigin: true },
    },
    allowedHosts: ['.trycloudflare.com'],
  },
})