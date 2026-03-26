import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { evalApiPlugin } from './server/eval-api'

export default defineConfig({
  plugins: [react(), evalApiPlugin()],
})
