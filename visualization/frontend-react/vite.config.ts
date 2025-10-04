import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api/traces': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Do not rewrite; keep /api/traces path for backend
      },
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path: string) => path.replace(/^\/api/, '')
      },
    }
  },
  build: {
    minify: false,
    sourcemap: true,
    target: 'esnext',
  },
  esbuild: {
    minify: false,
  },
  test: {
    // Use jsdom environment for DOM testing with React Testing Library
    environment: 'jsdom',
    globals: true,
    // Setup file to initialize testing library and globals
    setupFiles: './src/test/setup.ts',
    include: ['src/**/*.{test,spec}.{ts,tsx,js,jsx}'],
    coverage: {
      provider: 'c8',
      reporter: ['text', 'json', 'html']
    }
  }
} as any) as any
