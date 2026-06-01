import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Stethoscope, Mail, Github, FileText, Shield, Heart } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export default function Footer() {
  const { t } = useTranslation('common');
  const currentYear = new Date().getFullYear();
  const location = useLocation();
  const isHomePage = location.pathname === '/';

  const footerLinks = {
    platform: [
      { name: 'About', href: '/about' },
      { name: 'Features', href: '/features' },
      { name: t('footer.docs'), href: '/docs' },
      { name: 'Roadmap', href: '/roadmap' },
    ],
    tools: [
      { name: t('footer.viewer'), href: '/tools' },
      { name: t('buttons.upload'), href: '/tools' },
      { name: t('footer.analysis'), href: '/analyze' },
      { name: t('userMenu.aiModels'), href: '/models' },
    ],
    resources: [
      { name: 'DICOMweb Standard', href: 'https://www.dicomstandard.org/using/dicomweb', external: true },
      { name: 'OHIF Viewer', href: 'https://ohif.org', external: true },
      { name: 'Cornerstone.js', href: 'https://cornerstonejs.org', external: true },
      { name: 'Sample DICOM Files', href: 'https://www.rubomedical.com/dicom_files/', external: true },
    ],
    legal: [
      { name: 'Privacy Policy', href: '/privacy' },
      { name: 'Terms of Service', href: '/terms' },
      { name: t('footer.security'), href: '/security' },
      { name: 'Compliance', href: '/compliance' },
    ],
  };

  // Compact footer for non-home pages
  if (!isHomePage) {
    return (
      <footer className="bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-3 md:space-y-0">
            {/* Brand and Copyright */}
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 bg-medical-500 rounded-lg flex items-center justify-center">
                  <Stethoscope className="w-4 h-4 text-white" />
                </div>
                <span className="text-sm font-semibold medical-gradient-text">
                  MedAI Platform
                </span>
              </div>
              <span className="hidden sm:inline text-xs text-slate-400 dark:text-slate-600">•</span>
              <div className="text-xs text-slate-600 dark:text-slate-400">
                {t('footer.allRightsReserved', { year: currentYear })}
              </div>
            </div>

            {/* Legal Links */}
            <div className="flex items-center space-x-4 text-xs">
              {footerLinks.legal.map((link, index) => (
                <React.Fragment key={link.name}>
                  <Link
                    to={link.href}
                    className="text-slate-600 dark:text-slate-400 hover:text-medical-600 dark:hover:text-medical-400 transition-colors"
                  >
                    {link.name}
                  </Link>
                  {index < footerLinks.legal.length - 1 && (
                    <span className="text-slate-300 dark:text-slate-700">•</span>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      </footer>
    );
  }

  // Full footer for home page
  return (
    <footer className="bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8">
          {/* Brand Section */}
          <div className="lg:col-span-2">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-10 h-10 bg-medical-500 rounded-lg flex items-center justify-center">
                <Stethoscope className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold medical-gradient-text">
                MedAI Platform
              </span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-4 max-w-sm">
              {t('footer.tagline')}
            </p>
            <div className="flex items-center space-x-2 text-xs text-slate-500 dark:text-slate-500">
              <Shield className="w-4 h-4" />
              <span>{t('footer.compliance')}</span>
            </div>
          </div>

          {/* Platform Links */}
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 uppercase tracking-wider mb-4">
              {t('footer.platform')}
            </h3>
            <ul className="space-y-2">
              {footerLinks.platform.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-sm text-slate-600 dark:text-slate-400 hover:text-medical-600 dark:hover:text-medical-400 transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Tools Links */}
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 uppercase tracking-wider mb-4">
              {t('footer.tools')}
            </h3>
            <ul className="space-y-2">
              {footerLinks.tools.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-sm text-slate-600 dark:text-slate-400 hover:text-medical-600 dark:hover:text-medical-400 transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources Links */}
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 uppercase tracking-wider mb-4">
              {t('footer.resources')}
            </h3>
            <ul className="space-y-2">
              {footerLinks.resources.map((link) => (
                <li key={link.name}>
                  {link.external ? (
                    <a
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-slate-600 dark:text-slate-400 hover:text-medical-600 dark:hover:text-medical-400 transition-colors inline-flex items-center"
                    >
                      {link.name}
                      <svg className="w-3 h-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  ) : (
                    <Link
                      to={link.href}
                      className="text-sm text-slate-600 dark:text-slate-400 hover:text-medical-600 dark:hover:text-medical-400 transition-colors"
                    >
                      {link.name}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom Section */}
        <div className="mt-12 pt-8 border-t border-slate-200 dark:border-slate-800">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            {/* Copyright */}
            <div className="text-sm text-slate-600 dark:text-slate-400">
              {t('footer.allRightsReserved', { year: currentYear })}
              <span className="hidden sm:inline"> {t('footer.builtFor')}</span>
            </div>

            {/* Legal Links */}
            <div className="flex items-center space-x-6">
              {footerLinks.legal.map((link, index) => (
                <React.Fragment key={link.name}>
                  <Link
                    to={link.href}
                    className="text-sm text-slate-600 dark:text-slate-400 hover:text-medical-600 dark:hover:text-medical-400 transition-colors"
                  >
                    {link.name}
                  </Link>
                  {index < footerLinks.legal.length - 1 && (
                    <span className="text-slate-300 dark:text-slate-700">•</span>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Technology Stack */}
          <div className="mt-6 text-center">
            <p className="text-xs text-slate-500 dark:text-slate-500">
              {t('footer.poweredBy')}
            </p>
            <p className="text-xs text-slate-400 dark:text-slate-600 mt-1 flex items-center justify-center">
              {t('footer.madeWith')}
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
