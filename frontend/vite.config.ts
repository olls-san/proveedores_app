import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy API requests to the FastAPI backend during development.
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/sales': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/conciliations': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/inventory': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/me': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
});