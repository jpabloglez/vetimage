import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  Book,
  Code,
  FileText,
  Layers,
  Terminal,
  Zap,
  CheckCircle,
  ExternalLink,
  ChevronRight,
  Search,
  BookOpen,
  Package,
  GitBranch,
  Cpu,
} from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent, Input, Button } from '../components/ui';

const DocumentationPage: React.FC = () => {
  const { t } = useTranslation('common');
  const [searchQuery, setSearchQuery] = useState('');

  const documentationSections = [
    {
      id: 'getting-started',
      title: t('documentation.sections.gettingStarted'),
      icon: Zap,
      description: t('documentation.sections.gettingStartedDesc'),
      topics: [
        'Creating an account',
        'Uploading your first DICOM study',
        'Running AI analysis',
        'Viewing results in OHIF Viewer',
      ],
    },
    {
      id: 'api-reference',
      title: t('documentation.sections.apiReference'),
      icon: Code,
      description: t('documentation.sections.apiReferenceDesc'),
      topics: [
        'Authentication (JWT & API Keys)',
        'DICOM Upload API',
        'DICOMweb QIDO-RS Queries',
        'DICOMweb WADO-RS Image Retrieval',
        'AI Analysis API',
      ],
    },
    {
      id: 'dicom-standards',
      title: t('documentation.sections.dicomStandards'),
      icon: Layers,
      description: t('documentation.sections.dicomStandardsDesc'),
      topics: [
        'Supported DICOM Tags',
        'QIDO-RS Query Specification',
        'WADO-RS Retrieval Specification',
        'Metadata Format (JSON)',
        'OHIF Viewer Integration',
      ],
    },
    {
      id: 'ai-models',
      title: t('documentation.sections.aiModels'),
      icon: Cpu,
      description: t('documentation.sections.aiModelsDesc'),
      topics: [
        'Model Catalog',
        'Input Requirements',
        'Output Formats',
        'Performance Metrics',
        'Model Versioning',
      ],
    },
    {
      id: 'integration',
      title: t('documentation.sections.integration'),
      icon: GitBranch,
      description: t('documentation.sections.integrationDesc'),
      topics: [
        'PACS Integration',
        'Python SDK',
        'JavaScript SDK',
        'Webhook Callbacks',
        'Batch Processing',
      ],
    },
    {
      id: 'tutorials',
      title: t('documentation.sections.tutorials'),
      icon: BookOpen,
      description: t('documentation.sections.tutorialsDesc'),
      topics: [
        'Upload DICOM from Python',
        'Automated AI Analysis Pipeline',
        'Custom Viewer Integration',
        'Export Results to PACS',
      ],
    },
  ];

  const quickLinks = [
    { name: t('documentation.quickLinks.apiAuth'), href: '#api-reference', icon: Terminal },
    { name: t('documentation.quickLinks.uploadDicom'), href: '#getting-started', icon: Package },
    { name: t('documentation.quickLinks.dicomwebQueries'), href: '#dicom-standards', icon: Search },
    { name: t('documentation.quickLinks.aiModelCatalog'), href: '#ai-models', icon: Cpu },
  ];

  const externalResources = [
    {
      title: 'DICOM Standard',
      url: 'https://www.dicomstandard.org/',
      description: 'Official DICOM specification',
    },
    {
      title: 'DICOMweb',
      url: 'https://www.dicomstandard.org/using/dicomweb',
      description: 'RESTful services for DICOM',
    },
    {
      title: 'OHIF Viewer',
      url: 'https://ohif.org/',
      description: 'Open-source medical image viewer',
    },
    {
      title: 'Cornerstone.js',
      url: 'https://cornerstonejs.org/',
      description: 'JavaScript medical imaging library',
    },
  ];

  const filteredSections = documentationSections.filter(
    (section) =>
      section.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      section.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      section.topics.some((topic) => topic.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-medical-500 rounded-2xl mb-6">
            <Book className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl lg:text-5xl font-bold text-slate-900 dark:text-slate-100 mb-4">
            {t('documentation.title')}
          </h1>
          <p className="text-xl text-slate-600 dark:text-slate-400 max-w-3xl mx-auto">
            {t('documentation.subtitle')}
          </p>
        </div>

        {/* Search Bar */}
        <div className="max-w-2xl mx-auto mb-12">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
            <Input
              type="text"
              placeholder={t('documentation.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-12 py-3 text-lg"
            />
          </div>
        </div>

        {/* Quick Links */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
          {quickLinks.map((link) => {
            const Icon = link.icon;
            return (
              <a
                key={link.name}
                href={link.href}
                className="flex items-center gap-3 p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-medical-500 dark:hover:border-medical-500 transition-colors group"
              >
                <div className="p-2 bg-medical-50 dark:bg-medical-950/30 rounded-lg group-hover:bg-medical-100 dark:group-hover:bg-medical-900/50 transition-colors">
                  <Icon className="w-5 h-5 text-medical-600 dark:text-medical-400" />
                </div>
                <span className="font-medium text-slate-900 dark:text-slate-100">
                  {link.name}
                </span>
                <ChevronRight className="w-4 h-4 text-slate-400 ml-auto group-hover:text-medical-600 dark:group-hover:text-medical-400 transition-colors" />
              </a>
            );
          })}
        </div>

        {/* Documentation Sections */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-12">
          {filteredSections.map((section) => {
            const Icon = section.icon;
            return (
              <Card key={section.id} variant="medical" className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start gap-4">
                    <div className="p-3 bg-medical-50 dark:bg-medical-950/30 rounded-lg">
                      <Icon className="w-6 h-6 text-medical-600 dark:text-medical-400" />
                    </div>
                    <div className="flex-1">
                      <CardTitle className="mb-2">{section.title}</CardTitle>
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        {section.description}
                      </p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {section.topics.map((topic, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 text-medical-500 mt-0.5 flex-shrink-0" />
                        <a
                          href={`#${section.id}-${index}`}
                          className="text-slate-700 dark:text-slate-300 hover:text-medical-600 dark:hover:text-medical-400 transition-colors"
                        >
                          {topic}
                        </a>
                      </li>
                    ))}
                  </ul>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-4 w-full"
                    onClick={() => {
                      /* Navigate to section */
                    }}
                  >
                    {t('documentation.viewDocumentation')}
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* External Resources */}
        <Card variant="medical">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ExternalLink className="w-5 h-5" />
              {t('documentation.externalResources')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {externalResources.map((resource) => (
                <a
                  key={resource.title}
                  href={resource.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start gap-3 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors group"
                >
                  <FileText className="w-5 h-5 text-medical-600 dark:text-medical-400 mt-0.5" />
                  <div className="flex-1">
                    <h3 className="font-medium text-slate-900 dark:text-slate-100 mb-1 group-hover:text-medical-600 dark:group-hover:text-medical-400 transition-colors">
                      {resource.title}
                    </h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      {resource.description}
                    </p>
                  </div>
                  <ExternalLink className="w-4 h-4 text-slate-400 group-hover:text-medical-600 dark:group-hover:text-medical-400 transition-colors" />
                </a>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Need Help */}
        <div className="mt-12 text-center">
          <Card variant="medical" className="max-w-2xl mx-auto">
            <CardContent className="py-8">
              <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                {t('documentation.needHelp')}
              </h3>
              <p className="text-slate-600 dark:text-slate-400 mb-6">
                {t('documentation.needHelpDesc')}
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Link to="/auth/register">
                  <Button variant="medical" size="lg">
                    {t('documentation.getStarted')}
                  </Button>
                </Link>
                <a
                  href="mailto:support@medai-platform.com"
                  className="inline-block"
                >
                  <Button variant="outline" size="lg">
                    {t('documentation.contactSupport')}
                  </Button>
                </a>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default DocumentationPage;
