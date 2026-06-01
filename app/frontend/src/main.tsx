import React from 'react'
import ReactDOM from 'react-dom/client'
import './i18n' // Initialize i18n before React renders
import App from './App'
import './index.css'
// import './assets/css/base.css' // Commented out - conflicts with Tailwind layout

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
