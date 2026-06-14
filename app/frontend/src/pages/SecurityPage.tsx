import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  Shield,
  Lock,
  Key,
  Server,
  FileCheck,
  AlertTriangle,
  CheckCircle,
  Eye,
  Database,
  Cloud,
  UserCheck,
  ShieldCheck,
  FileText,
  Award,
  Activity,
} from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent, Button } from '../components/ui';

const SecurityPage: React.FC = () => {
  const { t } = useTranslation('common');

  const securityFeatures = [
    {
      icon: Lock,
      title: t('security.features.encryption'),
      description: t('security.features.encryptionDesc'),
      details: [
        'HTTPS/TLS 1.3 for all communications',
        'AES-256 encryption for stored data',
        'Encrypted database backups',
        'Secure key management (AWS KMS)',
      ],
    },
    {
      icon: ShieldCheck,
      title: t('security.features.hipaa'),
      description: t('security.features.hipaaDesc'),
      details: [
        'Owner personal data handled under GDPR principles',
        'Audit logging for all data access',
        'Configurable data retention & deletion',
        'DICOM de-identification tools built in',
      ],
    },
    {
      icon: Key,
      title: t('security.features.auth'),
      description: t('security.features.authDesc'),
      details: [
        'JWT-based session management',
        'API keys with scope-based permissions',
        'Multi-factor authentication (MFA)',
        'Role-based access control (RBAC)',
      ],
    },
    {
      icon: Database,
      title: t('security.features.isolation'),
      description: t('security.features.isolationDesc'),
      details: [
        'User-scoped data access',
        'Organization-level isolation',
        'No cross-tenant data sharing',
        'Secure data deletion on request',
      ],
    },
    {
      icon: Activity,
      title: t('security.features.auditLogging'),
      description: t('security.features.auditLoggingDesc'),
      details: [
        'All API requests logged',
        'User activity tracking',
        'Failed authentication attempts',
        'Data access audit trail',
      ],
    },
    {
      icon: Server,
      title: t('security.features.infrastructure'),
      description: t('security.features.infrastructureDesc'),
      details: [
        'AWS cloud infrastructure',
        'Automated backups (daily + hourly)',
        'DDoS protection',
        '99.9% uptime SLA',
      ],
    },
  ];

  // Honest posture — no fabricated certifications. Veterinary imaging is not
  // covered by HIPAA, and VetImage is not a regulated medical device.
  const certifications = [
    {
      icon: Lock,
      title: 'Encryption',
      description: 'TLS 1.3 in transit · AES-256 at rest',
      badge: 'Active',
    },
    {
      icon: FileCheck,
      title: 'GDPR Principles',
      description: 'Owner personal data — lawful basis, access & erasure',
      badge: 'Applied',
    },
    {
      icon: Activity,
      title: 'Audit Logging',
      description: 'Full access trail for clinic accountability',
      badge: 'Active',
    },
    {
      icon: AlertTriangle,
      title: 'Not a Medical Device',
      description: 'Not FDA-cleared · veterinary decision support only',
      badge: 'Disclosure',
    },
  ];

  const securityPractices = [
    {
      category: t('security.practices.dataProtection'),
      practices: [
        'De-identification of owner data when possible',
        'Automatic data retention policies',
        'Secure data export and deletion',
        'Regular security assessments',
      ],
    },
    {
      category: t('security.practices.accessControl'),
      practices: [
        'Principle of least privilege',
        'Time-limited session tokens',
        'IP whitelisting available',
        'Concurrent session limits',
      ],
    },
    {
      category: t('security.practices.monitoring'),
      practices: [
        '24/7 security monitoring',
        'Intrusion detection systems',
        'Automated threat response',
        'Regular penetration testing',
      ],
    },
    {
      category: t('security.practices.development'),
      practices: [
        'Secure coding practices',
        'Code review and static analysis',
        'Dependency vulnerability scanning',
        'Regular security updates',
      ],
    },
  ];

  const responsibleDisclosure = {
    title: t('security.disclosure.title'),
    description: t('security.disclosure.description'),
    steps: [
      'Email security@vetimage.app with details',
      'Include steps to reproduce (if applicable)',
      'Allow us 90 days to address the issue',
      'Do not publicly disclose until resolved',
    ],
    reward: t('security.disclosure.reward'),
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-medical-500 rounded-2xl mb-6">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl lg:text-5xl font-bold text-slate-900 dark:text-slate-100 mb-4">
            {t('security.title')}
          </h1>
          <p className="text-xl text-slate-600 dark:text-slate-400 max-w-3xl mx-auto">
            {t('security.subtitle')}
          </p>
        </div>

        {/* Trust Banner */}
        <Card variant="medical" className="mb-12 bg-gradient-to-r from-medical-50 to-teal-50 dark:from-medical-950/20 dark:to-teal-950/20 border-medical-200 dark:border-medical-800">
          <CardContent className="py-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="flex items-center gap-4">
                <div className="p-4 bg-white dark:bg-slate-800 rounded-full">
                  <ShieldCheck className="w-8 h-8 text-medical-600 dark:text-medical-400" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">
                    {t('security.hipaaCompliant')}
                  </h3>
                  <p className="text-slate-600 dark:text-slate-400">
                    {t('security.hipaaCompliantDesc')}
                  </p>
                </div>
              </div>
              <Link to="/auth/register">
                <Button variant="medical" size="lg">
                  {t('security.getStartedSecurely')}
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* AI Decision-Support Disclosure */}
        <Card className="mb-12 bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800">
          <CardContent className="py-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-amber-100 dark:bg-amber-900/50 rounded-lg flex-shrink-0">
                <AlertTriangle className="w-6 h-6 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-amber-900 dark:text-amber-100 mb-1">
                  {t('security.aiTitle')}
                </h3>
                <p className="text-amber-800 dark:text-amber-200 mb-2">
                  {t('security.aiDesc')}
                </p>
                <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
                  {t('security.notDevice')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Security Features */}
        <div className="mb-12">
          <h2 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-8">
            {t('security.securityFeatures')}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {securityFeatures.map((feature) => {
              const Icon = feature.icon;
              return (
                <Card key={feature.title} variant="medical" className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex items-start gap-4 mb-4">
                      <div className="p-3 bg-medical-50 dark:bg-medical-950/30 rounded-lg">
                        <Icon className="w-6 h-6 text-medical-600 dark:text-medical-400" />
                      </div>
                      <div className="flex-1">
                        <CardTitle className="text-lg mb-2">{feature.title}</CardTitle>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                          {feature.description}
                        </p>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {feature.details.map((detail, index) => (
                        <li key={index} className="flex items-start gap-2 text-sm">
                          <CheckCircle className="w-4 h-4 text-medical-500 mt-0.5 flex-shrink-0" />
                          <span className="text-slate-700 dark:text-slate-300">{detail}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Certifications */}
        <div className="mb-12">
          <h2 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-8">
            {t('security.certificationsTitle')}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {certifications.map((cert) => {
              const Icon = cert.icon;
              return (
                <Card key={cert.title} variant="medical" className="text-center">
                  <CardContent className="py-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-medical-50 dark:bg-medical-950/30 rounded-full mb-4">
                      <Icon className="w-8 h-8 text-medical-600 dark:text-medical-400" />
                    </div>
                    <h3 className="font-bold text-slate-900 dark:text-slate-100 mb-2">
                      {cert.title}
                    </h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
                      {cert.description}
                    </p>
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                        cert.badge === 'Active'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : cert.badge === 'Applied'
                          ? 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200'
                          : cert.badge === 'Disclosure'
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                          : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200'
                      }`}
                    >
                      {cert.badge}
                    </span>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Security Practices */}
        <div className="mb-12">
          <h2 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-8">
            {t('security.securityPractices')}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {securityPractices.map((section) => (
              <Card key={section.category} variant="medical">
                <CardHeader>
                  <CardTitle>{section.category}</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3">
                    {section.practices.map((practice, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <CheckCircle className="w-5 h-5 text-medical-500 mt-0.5 flex-shrink-0" />
                        <span className="text-slate-700 dark:text-slate-300">{practice}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Responsible Disclosure */}
        <Card variant="medical" className="mb-12 bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800">
          <CardHeader>
            <div className="flex items-start gap-4">
              <div className="p-3 bg-amber-100 dark:bg-amber-900/50 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-amber-600 dark:text-amber-400" />
              </div>
              <div className="flex-1">
                <CardTitle className="text-amber-900 dark:text-amber-100 mb-2">
                  {responsibleDisclosure.title}
                </CardTitle>
                <p className="text-amber-800 dark:text-amber-200">
                  {responsibleDisclosure.description}
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="bg-white dark:bg-slate-800 rounded-lg p-6 mb-4">
              <h4 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">
                {t('security.howToReport')}
              </h4>
              <ol className="space-y-2">
                {responsibleDisclosure.steps.map((step, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <span className="flex items-center justify-center w-6 h-6 bg-medical-100 dark:bg-medical-900 text-medical-600 dark:text-medical-400 rounded-full text-sm font-medium flex-shrink-0">
                      {index + 1}
                    </span>
                    <span className="text-slate-700 dark:text-slate-300 pt-0.5">{step}</span>
                  </li>
                ))}
              </ol>
            </div>
            <p className="text-sm text-amber-700 dark:text-amber-300">
              <strong>{t('security.bugBounty')}</strong> {responsibleDisclosure.reward}
            </p>
          </CardContent>
        </Card>

        {/* Contact Security Team */}
        <div className="text-center">
          <Card variant="medical" className="max-w-2xl mx-auto">
            <CardContent className="py-8">
              <Eye className="w-12 h-12 text-medical-600 dark:text-medical-400 mx-auto mb-4" />
              <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                {t('security.questionsTitle')}
              </h3>
              <p className="text-slate-600 dark:text-slate-400 mb-6">
                {t('security.questionsDesc')}
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <a
                  href="mailto:security@vetimage.app"
                  className="inline-block"
                >
                  <Button variant="medical" size="lg">
                    {t('security.contactSecurityTeam')}
                  </Button>
                </a>
                <Link to="/docs">
                  <Button variant="outline" size="lg">
                    {t('security.viewDocumentation')}
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default SecurityPage;
