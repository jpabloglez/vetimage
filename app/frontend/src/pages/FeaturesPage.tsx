import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  Brain,
  Eye,
  PawPrint,
  FileText,
  Activity,
  ShieldCheck,
  FileOutput,
  Tags,
  Share2,
  Globe,
  ArrowRight,
} from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent, Button } from '../components/ui';

const FeaturesPage: React.FC = () => {
  const { t } = useTranslation('common');

  const capabilities = [
    {
      icon: Brain,
      title: t('features.capabilities.analysis'),
      description: t('features.capabilities.analysisDesc'),
    },
    {
      icon: Eye,
      title: t('features.capabilities.viewer'),
      description: t('features.capabilities.viewerDesc'),
    },
    {
      icon: PawPrint,
      title: t('features.capabilities.patients'),
      description: t('features.capabilities.patientsDesc'),
    },
    {
      icon: FileText,
      title: t('features.capabilities.reports'),
      description: t('features.capabilities.reportsDesc'),
    },
    {
      icon: Activity,
      title: t('features.capabilities.monitoring'),
      description: t('features.capabilities.monitoringDesc'),
    },
    {
      icon: Globe,
      title: t('features.capabilities.multiClinic'),
      description: t('features.capabilities.multiClinicDesc'),
    },
  ];

  const tools = [
    {
      icon: Eye,
      title: t('features.tools.viewer'),
      description: t('features.tools.viewerDesc'),
    },
    {
      icon: ShieldCheck,
      title: t('features.tools.anonymizer'),
      description: t('features.tools.anonymizerDesc'),
    },
    {
      icon: FileOutput,
      title: t('features.tools.converter'),
      description: t('features.tools.converterDesc'),
    },
    {
      icon: Tags,
      title: t('features.tools.tagEditor'),
      description: t('features.tools.tagEditorDesc'),
    },
    {
      icon: Share2,
      title: t('features.tools.sharing'),
      description: t('features.tools.sharingDesc'),
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-medical-500 rounded-2xl mb-6">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl lg:text-5xl font-bold text-slate-900 dark:text-slate-100 mb-4">
            {t('features.title')}
          </h1>
          <p className="text-xl text-slate-600 dark:text-slate-400 max-w-3xl mx-auto">
            {t('features.subtitle')}
          </p>
        </div>

        {/* Platform capabilities */}
        <div className="mb-12">
          <h2 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-8">
            {t('features.capabilitiesTitle')}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {capabilities.map((item) => {
              const Icon = item.icon;
              return (
                <Card key={item.title} variant="medical" className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex items-start gap-4">
                      <div className="p-3 bg-medical-50 dark:bg-medical-950/30 rounded-lg">
                        <Icon className="w-6 h-6 text-medical-600 dark:text-medical-400" />
                      </div>
                      <div className="flex-1">
                        <CardTitle className="text-lg mb-2">{item.title}</CardTitle>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                          {item.description}
                        </p>
                      </div>
                    </div>
                  </CardHeader>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Tools */}
        <div className="mb-12">
          <h2 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            {t('features.toolsTitle')}
          </h2>
          <p className="text-slate-600 dark:text-slate-400 mb-8">
            {t('features.toolsSubtitle')}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {tools.map((tool) => {
              const Icon = tool.icon;
              return (
                <Card key={tool.title} variant="medical" className="hover:shadow-lg transition-shadow">
                  <CardContent className="py-6">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-2.5 bg-medical-50 dark:bg-medical-950/30 rounded-lg">
                        <Icon className="w-5 h-5 text-medical-600 dark:text-medical-400" />
                      </div>
                      <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                        {tool.title}
                      </h3>
                    </div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      {tool.description}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* CTA */}
        <div className="text-center">
          <Card variant="medical" className="max-w-2xl mx-auto bg-gradient-to-r from-medical-50 to-teal-50 dark:from-medical-950/20 dark:to-teal-950/20 border-medical-200 dark:border-medical-800">
            <CardContent className="py-10">
              <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                {t('features.ctaTitle')}
              </h3>
              <p className="text-slate-600 dark:text-slate-400 mb-6">
                {t('features.ctaDesc')}
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Link to="/auth/register">
                  <Button variant="medical" size="lg" rightIcon={ArrowRight}>
                    {t('features.ctaButton')}
                  </Button>
                </Link>
                <Link to="/docs">
                  <Button variant="outline" size="lg">
                    {t('features.ctaDocs')}
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

export default FeaturesPage;
