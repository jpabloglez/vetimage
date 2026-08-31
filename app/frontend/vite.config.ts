import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Content Security Policy for the SPA.
 *
 * Ships as Report-Only: violations show in the browser console without
 * blocking, so a missed directive can't take the viewer down. Switch the
 * header name to 'Content-Security-Policy' once a report-only run is clean.
 *
 * Notes on the directives that aren't obvious:
 *  - blob:/data: in img-src and worker-src are required by Cornerstone, which
 *    decodes DICOM frames into blobs and runs codecs in web workers.
 *  - 'unsafe-inline'/'unsafe-eval' in script-src are needed by the Vite dev
 *    server's HMR client. A production build should drop both — whatever
 *    serves the built bundle must set its own, stricter policy.
 *  - connect-src allows ws:/wss: for the Django Channels live updates.
 */
const CSP_REPORT_ONLY = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com data:",
  "img-src 'self' data: blob: https://images.unsplash.com",
  "worker-src 'self' blob:",
  "connect-src 'self' ws: wss: https://fonts.googleapis.com https://fonts.gstatic.com",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join('; ')

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    headers: {
      'Content-Security-Policy-Report-Only': CSP_REPORT_ONLY,
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      'X-Content-Type-Options': 'nosniff',
    },
    proxy: {
      '/api': {
        target: 'http://backend-vetimage:3080',
        changeOrigin: true,
      },
      '/users': {
        target: 'http://backend-vetimage:3080',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://backend-vetimage:3080',
        changeOrigin: true,
      },
      '/files': {
        target: 'http://backend-vetimage:3080',
        changeOrigin: true,
      },
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
