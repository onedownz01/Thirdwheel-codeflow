import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const devApiTarget = process.env.VITE_DEV_API_TARGET || 'http://127.0.0.1:8001';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      '/health': { target: devApiTarget, changeOrigin: true },
      '/telemetry': { target: devApiTarget, changeOrigin: true },
      '/parse': { target: devApiTarget, changeOrigin: true },
      '/intents': { target: devApiTarget, changeOrigin: true },
      '/occurrences': { target: devApiTarget, changeOrigin: true },
      '/trace': { target: devApiTarget, changeOrigin: true },
      '/fix': { target: devApiTarget, changeOrigin: true },
      '/ws': { target: devApiTarget, ws: true, changeOrigin: true },
    },
  },
  build: {
    chunkSizeWarningLimit: 2000,
    rollupOptions: {
      output: {
        manualChunks: {
          react_vendor: ['react', 'react-dom'],
          flow_vendor: ['reactflow', 'elkjs'],
          state_vendor: ['zustand']
        }
      }
    }
  }
});
