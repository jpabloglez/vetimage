import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// English
import enCommon from './locales/en/common.json';
import enLanding from './locales/en/landing.json';
import enAuth from './locales/en/auth.json';
import enAnalyze from './locales/en/analyze.json';
import enModels from './locales/en/models.json';
import enStatistics from './locales/en/statistics.json';
import enTools from './locales/en/tools.json';
import enReports from './locales/en/reports.json';
import enMonitor from './locales/en/monitor.json';
import enProfile from './locales/en/profile.json';
import enViewer from './locales/en/viewer.json';
import enNotifications from './locales/en/notifications.json';

// Spanish
import esCommon from './locales/es/common.json';
import esLanding from './locales/es/landing.json';
import esAuth from './locales/es/auth.json';
import esAnalyze from './locales/es/analyze.json';
import esModels from './locales/es/models.json';
import esStatistics from './locales/es/statistics.json';
import esTools from './locales/es/tools.json';
import esReports from './locales/es/reports.json';
import esMonitor from './locales/es/monitor.json';
import esProfile from './locales/es/profile.json';
import esViewer from './locales/es/viewer.json';
import esNotifications from './locales/es/notifications.json';

// Portuguese
import ptCommon from './locales/pt/common.json';
import ptLanding from './locales/pt/landing.json';
import ptAuth from './locales/pt/auth.json';
import ptAnalyze from './locales/pt/analyze.json';
import ptModels from './locales/pt/models.json';
import ptStatistics from './locales/pt/statistics.json';
import ptTools from './locales/pt/tools.json';
import ptReports from './locales/pt/reports.json';
import ptMonitor from './locales/pt/monitor.json';
import ptProfile from './locales/pt/profile.json';
import ptViewer from './locales/pt/viewer.json';
import ptNotifications from './locales/pt/notifications.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        common: enCommon,
        landing: enLanding,
        auth: enAuth,
        analyze: enAnalyze,
        models: enModels,
        statistics: enStatistics,
        tools: enTools,
        reports: enReports,
        monitor: enMonitor,
        profile: enProfile,
        viewer: enViewer,
        notifications: enNotifications,
      },
      es: {
        common: esCommon,
        landing: esLanding,
        auth: esAuth,
        analyze: esAnalyze,
        models: esModels,
        statistics: esStatistics,
        tools: esTools,
        reports: esReports,
        monitor: esMonitor,
        profile: esProfile,
        viewer: esViewer,
        notifications: esNotifications,
      },
      pt: {
        common: ptCommon,
        landing: ptLanding,
        auth: ptAuth,
        analyze: ptAnalyze,
        models: ptModels,
        statistics: ptStatistics,
        tools: ptTools,
        reports: ptReports,
        monitor: ptMonitor,
        profile: ptProfile,
        viewer: ptViewer,
        notifications: ptNotifications,
      },
    },
    fallbackLng: 'en',
    supportedLngs: ['en', 'es', 'pt'],
    defaultNS: 'common',
    ns: [
      'common', 'landing', 'auth', 'analyze', 'models',
      'statistics', 'tools', 'reports', 'monitor', 'profile',
      'viewer', 'notifications',
    ],
    interpolation: {
      escapeValue: false, // React already escapes
    },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'medai-language',
      caches: ['localStorage'],
    },
  });

export default i18n;
