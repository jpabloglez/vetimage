import React, { useState, Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useTranslation } from 'react-i18next';

// Contexts
import { ThemeProvider, AuthProvider, LanguageProvider } from './contexts';

// Components (always loaded — part of the app shell)
import Navbar from './components/navbars/Navbar';
import Footer from './components/footers/Footer';
import ProtectedRoute from './components/ProtectedRoute';
import { KeyboardShortcutsHelp } from './components/ui/KeyboardShortcutsHelp';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

// Pages — lazily loaded so each route gets its own JS chunk
const LandingPage      = lazy(() => import('./pages/LandingPage'));
const ToolsPage        = lazy(() => import('./pages/ToolsPage'));
const ModelsPage       = lazy(() => import('./pages/ModelsPage'));
const ModelDetailsPage = lazy(() => import('./pages/ModelDetailsPage'));
const Dashboard        = lazy(() => import('./pages/DashboardPage'));
const ReportDetailPage = lazy(() => import('./pages/ReportDetailPage'));
const AnalyzePage      = lazy(() => import('./pages/AnalyzePage'));
const PatientsPage     = lazy(() => import('./pages/PatientsPage'));
const CalendarPage     = lazy(() => import('./pages/CalendarPage'));
const OwnerPortalPage  = lazy(() => import('./pages/OwnerPortalPage'));
const OwnerReportPage  = lazy(() => import('./pages/OwnerReportPage'));
const ReferralPackagePage = lazy(() => import('./pages/ReferralPackagePage'));
const AuditLogPage     = lazy(() => import('./pages/AuditLogPage'));
const MonitorPage      = lazy(() => import('./pages/MonitorPage'));
const StatisticsPage   = lazy(() => import('./pages/StatisticsPage'));
const DocumentationPage = lazy(() => import('./pages/DocumentationPage'));
const SecurityPage     = lazy(() => import('./pages/SecurityPage'));
const ProfilePage      = lazy(() =>
  import('./pages/ProfilePage').then((m) => ({ default: m.ProfilePage }))
);

// Auth pages — grouped in one chunk since they're rarely visited after login
const LoginPage           = lazy(() =>
  import('./pages/auth').then((m) => ({ default: m.LoginPage }))
);
const RegisterPage        = lazy(() =>
  import('./pages/auth').then((m) => ({ default: m.RegisterPage }))
);
const ForgotPasswordPage  = lazy(() =>
  import('./pages/auth').then((m) => ({ default: m.ForgotPasswordPage }))
);
const ResetPasswordPage   = lazy(() =>
  import('./pages/auth').then((m) => ({ default: m.ResetPasswordPage }))
);

/** Minimal full-page spinner shown while a lazy chunk loads */
const PageLoader = () => (
  <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
    <div className="w-8 h-8 border-4 border-medical-500 border-t-transparent rounded-full animate-spin" />
  </div>
);

// Placeholder components for other pages
const NotFoundPage = () => {
  const { t } = useTranslation('common');
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-slate-300 dark:text-slate-600 mb-4">{t('notFound.title')}</h1>
        <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 mb-4">{t('notFound.heading')}</h2>
        <p className="text-slate-600 dark:text-slate-400 mb-8">
          {t('notFound.message')}
        </p>
        <a
          href="/"
          className="medical-button-primary"
        >
          {t('notFound.returnHome')}
        </a>
      </div>
    </div>
  );
};

/** Inner app shell — lives inside Router so hooks like useNavigate work */
const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [showShortcuts, setShowShortcuts] = useState(false);
  const shortcuts = useKeyboardShortcuts(() => setShowShortcuts(true), [
    { key: 'Escape', label: 'Esc', description: 'Close modal / dialog', action: () => setShowShortcuts(false) },
  ]);

  return (
    <>
      {children}
      <KeyboardShortcutsHelp
        isOpen={showShortcuts}
        onClose={() => setShowShortcuts(false)}
        shortcuts={shortcuts}
      />
    </>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <LanguageProvider>
        <Router>
          <AppShell>
          <div className="min-h-screen bg-slate-50 dark:bg-slate-900 transition-colors duration-300">
            <Navbar />

            <main className="flex-1">
              <Suspense fallback={<PageLoader />}>
              <Routes>
                {/* Public Routes */}
                <Route path="/" element={<LandingPage />} />
                {/* Public owner-facing shared report (no auth — token in URL) */}
                <Route path="/shared/:token" element={<OwnerReportPage />} />
                {/* Public specialist-facing referral package (no auth — token in URL) */}
                <Route path="/referral/:token" element={<ReferralPackagePage />} />

                {/* Authentication Routes (redirect if already authenticated) */}
                <Route
                  path="/auth/login"
                  element={
                    <ProtectedRoute requireAuth={false}>
                      <LoginPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/auth/register"
                  element={
                    <ProtectedRoute requireAuth={false}>
                      <RegisterPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/auth/forgot-password"
                  element={
                    <ProtectedRoute requireAuth={false}>
                      <ForgotPasswordPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/auth/reset-password"
                  element={
                    <ProtectedRoute requireAuth={false}>
                      <ResetPasswordPage />
                    </ProtectedRoute>
                  }
                />

                {/* Public Models Routes - Allow browsing before login */}
                <Route path="/models" element={<ModelsPage />} />
                <Route path="/models/:modelKey" element={<ModelDetailsPage />} />

                {/* Public Information Pages */}
                <Route path="/docs" element={<DocumentationPage />} />
                <Route path="/security" element={<SecurityPage />} />

                {/* Protected Routes */}
                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/reports/:id"
                  element={
                    <ProtectedRoute>
                      <ReportDetailPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/patients"
                  element={
                    <ProtectedRoute>
                      <PatientsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/calendar"
                  element={
                    <ProtectedRoute>
                      <CalendarPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/portal"
                  element={
                    <ProtectedRoute>
                      <OwnerPortalPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/analyze"
                  element={
                    <ProtectedRoute>
                      <AnalyzePage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/tools"
                  element={
                    <ProtectedRoute>
                      <ToolsPage />
                    </ProtectedRoute>
                  }
                />
                <Route path="/reports" element={<Navigate to="/analyze" replace />} />
                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <ProfilePage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/monitor"
                  element={
                    <ProtectedRoute>
                      <MonitorPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/statistics"
                  element={
                    <ProtectedRoute>
                      <StatisticsPage />
                    </ProtectedRoute>
                  }
                />
                <Route path="/audit-report" element={<Navigate to="/audit-log" replace />} />
                <Route
                  path="/audit-log"
                  element={
                    <ProtectedRoute>
                      <AuditLogPage />
                    </ProtectedRoute>
                  }
                />

                {/* Role-based Protected Routes */}
                <Route
                  path="/admin"
                  element={
                    <ProtectedRoute allowedRoles={['admin']}>
                      <div className="p-8">
                        <h1 className="text-2xl font-bold">Admin Panel</h1>
                        <p>This page is only accessible to administrators.</p>
                      </div>
                    </ProtectedRoute>
                  }
                />

                {/* Redirect /app to /dashboard */}
                <Route path="/app" element={<Navigate to="/dashboard" replace />} />

                {/* 404 Page */}
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
              </Suspense>
            </main>

            {/* Footer only on non-auth pages */}
            <Suspense fallback={null}>
            <Routes>
              <Route path="/auth/*" element={null} />
              <Route path="*" element={<Footer />} />
            </Routes>
            </Suspense>

            {/* Toast Notifications */}
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                className: 'medical-card text-sm',
                style: {
                  background: 'rgb(var(--color-bg-tertiary))',
                  color: 'rgb(var(--color-text-primary))',
                  border: '1px solid rgb(var(--color-border-primary))',
                },
              }}
            />
          </div>
          </AppShell>
        </Router>
        </LanguageProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
