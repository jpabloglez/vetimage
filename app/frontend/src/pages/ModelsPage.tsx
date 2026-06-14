/**
 * ModelsPage Component
 *
 * AI Model Catalog page displaying all available AI models.
 * Users can browse, filter, and view details of AI models.
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { apiClient, AIModel } from '../utils/api';
import ModelCard from '../components/models/ModelCard';
import Card, { CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import Input from '../components/ui/Input';

const ModelsPage: React.FC = () => {
  const { t } = useTranslation('models');
  const [models, setModels] = useState<AIModel[]>([]);
  const [filteredModels, setFilteredModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isNetworkError, setIsNetworkError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedSpecies, setSelectedSpecies] = useState<string>('all');

  const SPECIES_OPTIONS = ['canine', 'feline', 'equine', 'bovine', 'avian', 'exotic'];

  useEffect(() => {
    const fetchModels = async () => {
      try {
        setLoading(true);
        setError(null);
        setIsNetworkError(false);
        const data = await apiClient.getAIModels();
        setModels(data);
        setFilteredModels(data);
      } catch (err: any) {
        if (err instanceof TypeError) {
          setIsNetworkError(true);
          setError(t('errorUnavailable'));
        } else {
          setError(err.detail || err.error || t('errorLoading'));
        }
      } finally {
        setLoading(false);
      }
    };

    fetchModels();
  }, [retryKey, t]);

  // Filter models based on search and type
  useEffect(() => {
    let filtered = models;

    // Filter by type
    if (selectedType !== 'all') {
      filtered = filtered.filter(model => model.model_type === selectedType);
    }

    // Filter by species (species-agnostic models — empty list — always match)
    if (selectedSpecies !== 'all') {
      filtered = filtered.filter(model => {
        const sp = model.supported_species ?? [];
        return sp.length === 0 || sp.includes(selectedSpecies);
      });
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(model =>
        model.name.toLowerCase().includes(query) ||
        model.description.toLowerCase().includes(query) ||
        (model.tags && model.tags.some(tag => tag.toLowerCase().includes(query))) ||
        (model.organization && model.organization.toLowerCase().includes(query))
      );
    }

    setFilteredModels(filtered);
  }, [models, searchQuery, selectedType, selectedSpecies]);

  // Get unique model types
  const modelTypes = Array.from(new Set(models.map(m => m.model_type)));

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medical-500 mx-auto mb-4"></div>
          <p className="text-slate-600 dark:text-slate-400">{t('loading')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="text-center py-8">
            <svg className="w-16 h-16 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
              {isNetworkError ? t('errorUnavailableTitle') : t('errorTitle')}
            </h2>
            <p className="text-slate-600 dark:text-slate-400 mb-4">{error}</p>
            {isNetworkError && (
              <button
                onClick={() => setRetryKey((k) => k + 1)}
                className="px-4 py-2 bg-medical-500 hover:bg-medical-600 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {t('retry')}
              </button>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 dark:text-slate-100 mb-2 medical-gradient-text">
            {t('title')}
          </h1>
          <p className="text-lg text-slate-600 dark:text-slate-400">
            {t('subtitle')}
          </p>
        </div>

        {/* Search and Filters */}
        <Card variant="medical" className="mb-6">
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Search */}
              <div>
                <label htmlFor="search" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  {t('search')}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <svg className="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <Input
                    id="search"
                    type="text"
                    placeholder={t('searchPlaceholder')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              {/* Type Filter */}
              <div>
                <label htmlFor="type" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  {t('modelType')}
                </label>
                <select
                  id="type"
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-medical-500 focus:border-transparent"
                >
                  <option value="all">{t('allTypes')}</option>
                  {modelTypes.map(type => (
                    <option key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Species Filter */}
              <div>
                <label htmlFor="species" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  {t('species', 'Species')}
                </label>
                <select
                  id="species"
                  value={selectedSpecies}
                  onChange={(e) => setSelectedSpecies(e.target.value)}
                  className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-medical-500 focus:border-transparent"
                >
                  <option value="all">{t('allSpecies', 'All species')}</option>
                  {SPECIES_OPTIONS.map(sp => (
                    <option key={sp} value={sp}>
                      {sp.charAt(0).toUpperCase() + sp.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Results Count */}
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {t('showing', { count: filteredModels.length, total: models.length })}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Models Grid */}
        {filteredModels.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <svg className="w-16 h-16 text-slate-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
                {t('noModels')}
              </h3>
              <p className="text-slate-600 dark:text-slate-400">
                {t('noModelsHint')}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredModels.map(model => (
              <ModelCard key={model.key} model={model} />
            ))}
          </div>
        )}

        {/* Info Section */}
        <Card variant="glass" className="mt-8">
          <CardHeader>
            <CardTitle>{t('about.title')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-slate-700 dark:text-slate-300 mb-4">
              {t('about.description')}
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex items-start">
                <svg className="w-6 h-6 text-medical-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <div>
                  <h4 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">
                    {t('about.validated')}
                  </h4>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Each model lists its species, version, datasets, and known limitations — review them before clinical use
                  </p>
                </div>
              </div>
              <div className="flex items-start">
                <svg className="w-6 h-6 text-medical-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                <div>
                  <h4 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">
                    {t('about.openSource')}
                  </h4>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Most models are available under open source licenses with full documentation
                  </p>
                </div>
              </div>
              <div className="flex items-start">
                <svg className="w-6 h-6 text-medical-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <div>
                  <h4 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">
                    {t('about.productionReady')}
                  </h4>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Optimized for deployment with comprehensive API support and monitoring
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ModelsPage;
