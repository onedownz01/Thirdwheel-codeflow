import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1'
  },
  optimizeDeps: {
    exclude: ['elkjs'],
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
