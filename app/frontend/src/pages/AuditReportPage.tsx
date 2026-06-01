/**
 * Audit Report Page
 *
 * Filter, preview, and download audit trail reports.
 */

import React, { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Download, Eye, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient } from '../utils/api';
import AuditReportFilters, { type AuditFilters } from '../components/audit/AuditReportFilters';
import AuditReportPreview from '../components/audit/AuditReportPreview';

const AuditReportPage: React.FC = () => {
  const { t } = useTranslation('common');
  const [filters, setFilters] = useState<AuditFilters>({});
  const [preview, setPreview] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const handlePreview = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getAuditReportPreview(filters);
      setPreview(data);
    } catch {
      toast.error(t('audit.loadError'));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const handleDownload = useCallback(async () => {
    setDownloading(true);
    try {
      await apiClient.downloadAuditReportPdf(filters);
    } catch {
      toast.error(t('audit.downloadError'));
    } finally {
      setDownloading(false);
    }
  }, [filters]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 pt-20">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold medical-gradient-text mb-2">{t('audit.title')}</h1>
          <p className="text-slate-600 dark:text-slate-400">
            {t('audit.subtitle')}
          </p>
        </div>

        {/* Filters */}
        <div className="medical-card p-6 mb-6">
          <AuditReportFilters filters={filters} onChange={setFilters} />

          <div className="flex gap-3 mt-4">
            <button
              onClick={handlePreview}
              disabled={loading}
              className="medical-button-primary flex items-center gap-2 px-4 py-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
              {t('audit.preview')}
            </button>

            <button
              onClick={handleDownload}
              disabled={downloading}
              className="flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              {t('audit.downloadPdf')}
            </button>
          </div>
        </div>

        {/* Preview */}
        {preview && <AuditReportPreview content={preview} />}
      </div>
    </div>
  );
};

export default AuditReportPage;
