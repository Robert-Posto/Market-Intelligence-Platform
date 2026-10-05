import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * În dezvoltare, interfața nouă cere datele de la serverul Python de acum
 * (app/server.py, :8765): API-ul rămâne același până trece pe Fastify, deci
 * cifrele de pe pagina nouă se pot compara direct cu cele de pe pagina veche.
 * Siglele, vizualizatorul PDF și harta vin tot de acolo până sunt mutate.
 */
const PYTHON = 'http://localhost:8765'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': PYTHON,
      '/logos': PYTHON,
      '/pdf': PYTHON,
      '/pdf.html': PYTHON,
      '/harta.html': PYTHON,
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1500,
  },
})
