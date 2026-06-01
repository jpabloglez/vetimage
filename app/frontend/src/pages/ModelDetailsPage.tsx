/**
 * ModelDetailsPage Component
 *
 * Comprehensive model card page displaying all AI model information:
 * - Basic information and description
 * - Authors and organization
 * - Publications and citations
 * - Code repositories and resources
 * - Licensing information
 * - Performance metrics
 * - Use cases and limitations
 * - Community and support links
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient, AIModel } from '../utils/api';
import Card, { CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import Button from '../components/ui/Button';

const ModelDetailsPage: React.FC = () => {
  const { t } = useTranslation('models');
  const { modelKey } = useParams<{ modelKey: string }>();
  const navigate = useNavigate();
  const [model, setModel] = useState<AIModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchModel = async () => {
      if (!modelKey) {
        setError('Model key not provided');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const data = await apiClient.getAIModel(modelKey);
        setModel(data);
      } catch (err: any) {
        console.error('Error fetching model:', err);
        setError(err.detail || err.error || 'Failed to load model details');
      } finally {
        setLoading(false);
      }
    };

    fetchModel();
  }, [modelKey]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medical-500 mx-auto mb-4"></div>
          <p className="text-slate-600 dark:text-slate-400">{t('details.loading')}</p>
        </div>
      </div>
    );
  }

  if (error || !model) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="text-center py-8">
            <svg className="w-16 h-16 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">Error</h2>
            <p className="text-slate-600 dark:text-slate-400 mb-4">{error || t('details.notFound')}</p>
            <Button variant="medical" onClick={() => navigate('/models')}>
              {t('details.backToModels')}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={() => navigate('/models')}
          className="mb-6"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          {t('details.backToModels')}
        </Button>

        {/* Header Section */}
        <Card variant="medical" className="mb-6">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle as="h1" className="text-3xl mb-2">{model.name}</CardTitle>
                <p className="text-lg text-slate-600 dark:text-slate-400">
                  {t('details.version', { version: model.version })}
                  {model.organization && ` • ${model.organization}`}
                </p>
              </div>
              <span className="px-4 py-2 bg-medical-100 text-medical-800 dark:bg-medical-900 dark:text-medical-200 rounded-lg text-sm font-medium">
                {model.model_type.charAt(0).toUpperCase() + model.model_type.slice(1)}
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-slate-700 dark:text-slate-300 text-lg leading-relaxed">
              {model.description}
            </p>

            {/* Quick Actions */}
            <div className="flex flex-wrap gap-3 mt-6">
              {model.github_url && (
                <Button variant="outline" onClick={() => window.open(model.github_url, '_blank')}>
                  <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
                    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                  </svg>
                  {t('details.github')}
                </Button>
              )}
              {model.paper_url && (
                <Button variant="outline" onClick={() => window.open(model.paper_url, '_blank')}>
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  {t('details.paper')}
                </Button>
              )}
              {model.documentation_url && (
                <Button variant="outline" onClick={() => window.open(model.documentation_url, '_blank')}>
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                  {t('details.documentation')}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content - Left Column (2/3) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Publications */}
            {model.publication_title && (
              <Card>
                <CardHeader>
                  <CardTitle>{t('details.publication')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-2">
                    {model.publication_title}
                  </h3>
                  {model.publication_journal && (
                    <p className="text-slate-600 dark:text-slate-400 mb-1">
                      {model.publication_journal}
                      {model.publication_year && `, ${model.publication_year}`}
                    </p>
                  )}
                  {model.publication_doi && (
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">
                      {t('details.doi', { doi: model.publication_doi })}
                    </p>
                  )}
                  {model.citation && (
                    <div className="bg-slate-50 dark:bg-slate-800 p-3 rounded-lg mt-3">
                      <p className="text-xs font-mono text-slate-700 dark:text-slate-300">
                        {model.citation}
                      </p>
                    </div>
                  )}
                  {model.publication_url && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.open(model.publication_url, '_blank')}
                      className="mt-3"
                    >
                      {t('details.viewPublication')}
                    </Button>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Performance Metrics */}
            {model.performance_metrics && Object.keys(model.performance_metrics).length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>{t('details.performance')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    {Object.entries(model.performance_metrics).map(([key, value]) => (
                      <div key={key} className="bg-slate-50 dark:bg-slate-800 p-4 rounded-lg">
                        <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">
                          {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </p>
                        <p className="text-2xl font-bold text-medical-600 dark:text-medical-400">
                          {typeof value === 'number' ? value.toFixed(3) : value}
                        </p>
                      </div>
                    ))}
                  </div>
                  {(model.validation_dataset || model.training_dataset) && (
                    <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                      {model.training_dataset && (
                        <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">
                          <span className="font-medium">{t('details.training')}</span> {model.training_dataset}
                        </p>
                      )}
                      {model.validation_dataset && (
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                          <span className="font-medium">{t('details.validation')}</span> {model.validation_dataset}
                        </p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Use Cases */}
            {model.use_cases && model.use_cases.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>{t('details.useCases')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {model.use_cases.map((useCase, index) => (
                      <li key={index} className="flex items-start">
                        <svg className="w-5 h-5 text-medical-500 mr-2 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="text-slate-700 dark:text-slate-300">{useCase}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* Limitations */}
            {model.limitations && (
              <Card>
                <CardHeader>
                  <CardTitle>{t('details.limitations')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 p-4 rounded-lg">
                    <div className="flex items-start">
                      <svg className="w-5 h-5 text-yellow-600 dark:text-yellow-500 mr-2 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-line">
                        {model.limitations}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar - Right Column (1/3) */}
          <div className="space-y-6">
            {/* Technical Details */}
            <Card>
              <CardHeader>
                <CardTitle>{t('details.technical')}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                    {t('details.modelType')}
                  </p>
                  <p className="text-slate-900 dark:text-slate-100">
                    {model.model_type.charAt(0).toUpperCase() + model.model_type.slice(1)}
                  </p>
                </div>
                {model.supported_modalities && model.supported_modalities.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      {t('details.supportedModalities')}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {model.supported_modalities.map((modality, index) => (
                        <span key={index} className="px-2 py-1 bg-medical-100 text-medical-800 dark:bg-medical-900 dark:text-medical-200 rounded text-sm">
                          {modality}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {model.anatomical_regions && model.anatomical_regions.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      {t('details.anatomicalRegions')}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {model.anatomical_regions.map((region, index) => (
                        <span key={index} className="px-2 py-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded text-sm">
                          {region}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {model.medical_domains && model.medical_domains.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      {t('details.medicalDomains')}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {model.medical_domains.map((domain, index) => (
                        <span key={index} className="px-2 py-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded text-sm">
                          {domain}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Authors */}
            {model.authors && model.authors.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>{t('details.authors')}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {model.authors.map((author, index) => (
                    <div key={index}>
                      <p className="font-medium text-slate-900 dark:text-slate-100">
                        {author.name}
                      </p>
                      {author.affiliation && (
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                          {author.affiliation}
                        </p>
                      )}
                      {author.email && (
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {author.email}
                        </p>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* License */}
            {model.license_name && (
              <Card>
                <CardHeader>
                  <CardTitle>{t('details.license')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center mb-2">
                    <svg className="w-5 h-5 text-medical-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    <span className="font-medium text-slate-900 dark:text-slate-100">
                      {model.license_name}
                    </span>
                  </div>
                  {model.license_url && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.open(model.license_url, '_blank')}
                      className="w-full"
                    >
                      {t('details.viewLicense')}
                    </Button>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Tags */}
            {model.tags && model.tags.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>{t('details.tags')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {model.tags.map((tag, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded text-xs"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Support */}
            {model.support_url && (
              <Card>
                <CardHeader>
                  <CardTitle>{t('details.support')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <Button
                    variant="outline"
                    onClick={() => window.open(model.support_url, '_blank')}
                    className="w-full"
                  >
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                    {t('details.getSupport')}
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModelDetailsPage;
