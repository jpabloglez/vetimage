/**
 * Monitor Page
 *
 * Real-time monitoring dashboard for analysis jobs, gateway transfers, and audit reports.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Activity, Download, Eye, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { JobMonitorPanel } from '../components/monitor/JobMonitorPanel';
import { DicomTransferPanel } from '../components/monitor/DicomTransferPanel';
import { ProfileCompletionModal } from '../components/monitor/ProfileCompletionModal';
import AuditReportFilters, { type AuditFilters } from '../components/audit/AuditReportFilters';
import AuditReportPreview from '../components/audit/AuditReportPreview';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../utils/api';

type TabType = 'analyses' | 'transfers' | 'audit';

// ─── AuditTab ─────────────────────────────────────────────────────────────────

const AuditTab: React.FC = () => {
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
  }, [filters, t]);

  const handleDownload = useCallback(async () => {
    setDownloading(true);
    try {
      await apiClient.downloadAuditReportPdf(filters);
    } catch {
      toast.error(t('audit.downloadError'));
    } finally {
      setDownloading(false);
    }
  }, [filters, t]);

  return (
    <div>
      {/* Filters + actions */}
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
  );
};

export const MonitorPage: React.FC = () => {
  const { t } = useTranslation('monitor');
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<TabType>('analyses');
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [profileChecked, setProfileChecked] = useState(false);

  /**
   * Check if user needs to complete profile
   */
  useEffect(() => {
    const checkProfile = async () => {
      if (!user || profileChecked) return;

      try {
        // Get user profile to check if department is set
        const profile = await apiClient.getProfile();

        // TODO: Check if profile has department field
        // For now, we'll skip the modal check as the User type doesn't include profile
        // In a real implementation, you'd extend the User type to include profile data

        setProfileChecked(true);
      } catch (error) {
        console.error('Failed to check profile:', error);
        setProfileChecked(true);
      }
    };

    checkProfile();
  }, [user, profileChecked]);

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Page Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Activity className="w-8 h-8 text-medical-500" />
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
            {t('title')}
          </h1>
        </div>
        <p className="text-slate-600 dark:text-slate-400">
          {t('subtitle')}
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="mb-6 border-b border-slate-200 dark:border-slate-700">
        <nav className="flex gap-8">
          {(
            [
              { key: 'analyses', label: t('tabs.aiAnalyses') },
              { key: 'transfers', label: t('tabs.dicomTransfers') },
              { key: 'audit', label: t('tabs.audit') },
            ] as { key: TabType; label: string }[]
          ).map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`pb-4 px-2 font-medium transition-colors ${
                activeTab === tab.key
                  ? 'border-b-2 border-medical-500 text-medical-600 dark:text-medical-400'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Panel Content */}
      {activeTab === 'analyses'  && <JobMonitorPanel />}
      {activeTab === 'transfers' && <DicomTransferPanel />}
      {activeTab === 'audit'     && <AuditTab />}

      {/* Profile Completion Modal */}
      {showProfileModal && (
        <ProfileCompletionModal
          onClose={() => setShowProfileModal(false)}
          onComplete={() => {
            setShowProfileModal(false);
            // Optionally refresh the page or reload user data
          }}
        />
      )}
    </div>
  );
};

export default MonitorPage;
