import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Content Security Policy for the SPA.
 *
 * **Enforced.** It shipped report-only pending a "clean run" that nothing was
 * set up to observe — neither policy had a `report-uri`, so violations went to
 * whichever console happened to be open. That run has now been done properly:
 * a browser drove every route in the router, signed out and signed in,
 * including the Cornerstone viewer (the highest-risk page — blob URLs, web
 * workers, DICOM codecs), collecting `securitypolicyviolation` events. The SPA
 * produced zero violations, so enforcing changes no behaviour that was
 * observed; `report-uri` is now set so anything missed shows up in the backend
 * logs instead of silently breaking a page.
 *
 * Scope caveat, because it is easy to misread: these headers come from the
 * Vite **dev server**, so they apply only to `npm run dev`. A built bundle
 * served by anything else carries no CSP at all unless that server sets one.
 * (Today the prod compose file inherits `command: npm run dev`, so this is
 * also the production policy — which is its own problem, not this file's.)
 *
 * Note too that script-src keeps 'unsafe-inline'/'unsafe-eval' for HMR, so
 * enforcing this is not XSS-proof. What it does buy is real: frame-ancestors
 * (clickjacking), object-src, base-uri, form-action, and a connect-src that
 * pins where the app may talk to.
 *
 * Notes on the directives that aren't obvious:
 *  - blob:/data: in img-src and worker-src are required by Cornerstone, which
 *    decodes DICOM frames into blobs and runs codecs in web workers.
 *  - 'unsafe-inline'/'unsafe-eval' in script-src are needed by the Vite dev
 *    server's HMR client. A production build should drop both — whatever
 *    serves the built bundle must set its own, stricter policy.
 *  - connect-src must include the backend origin (VITE_API_URL), not just
 *    'self': the SPA is served from :3001 but calls the API on :3081, so a
 *    bare 'self' put every API call and every WebSocket in violation. It was
 *    report-only, so nothing broke — but enforcing it would have taken the
 *    whole app down. ws:/wss: cover the Channels live updates.
 */
// The SPA is served from :3001 but calls the API on a different origin.
const API_ORIGIN = process.env.VITE_API_URL || 'http://localhost:3081'

// Violations post to the backend, which logs them (core/csp_report.py).
const CSP_REPORT_URI = `${API_ORIGIN}/api/csp-report/`

const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com data:",
  "img-src 'self' data: blob: https://images.unsplash.com",
  "worker-src 'self' blob:",
  `connect-src 'self' ${API_ORIGIN} ${API_ORIGIN.replace(/^http/, 'ws')} ws: wss: https://fonts.googleapis.com https://fonts.gstatic.com`,
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
  `report-uri ${CSP_REPORT_URI}`,
].join('; ')

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    headers: {
      'Content-Security-Policy': CSP,
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
