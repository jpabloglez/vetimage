import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://backend-openmedlab:3080',
        changeOrigin: true,
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Core React runtime — changes rarely, maximises cache lifetime
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // Chart library — large and independent
          'vendor-charts': ['recharts'],
          // Form handling
          'vendor-forms': ['react-hook-form', '@hookform/resolvers', 'zod'],
          // OHIF medical viewer — very large, split into its own chunk
          'vendor-ohif': [
            '@ohif/core',
            '@ohif/viewer',
            '@ohif/extension-cornerstone',
            '@ohif/extension-default',
          ],
          // Cornerstone imaging toolkit
          'vendor-cornerstone': [
            'cornerstone-core',
            'cornerstone-tools',
            'cornerstone-wado-image-loader',
            'cornerstone-math',
            'dicom-parser',
          ],
        },
      },
    },
  },
})
