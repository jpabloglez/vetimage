import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Brain, CheckCircle2, FileText, LayoutDashboard, Loader2, Zap } from 'lucide-react';

import { apiClient } from '../utils/api';
import type { Report } from '../types/api';
import { useWebSocket } from '../hooks/useWebSocket';
import PageHeader from '../components/ui/PageHeader';

const RECENT_LIMIT = 6;

/** Normalize the DICOM/report placeholder "N/A" (and empty values) to an em-dash. */
const field = (value?: string): string => (value && value !== 'N/A' ? value : '—');

/** The report/study date, falling back to the record's created date. */
const reportDate = (report: Report): string => {
  const raw = report.patient_info?.study_date;
  const iso = raw && raw !== 'N/A' ? raw : report.created_at;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString();
};

/** Large call-to-action tile that navigates to a specific area of the app. */
const ActionTile: React.FC<{
  to: string;
  icon: React.ElementType;
  title: string;
  description: string;
}> = ({ to, icon: Icon, title, description }) => (
  <Link
    to={to}
    className="medical-card p-6 group flex items-start gap-4 hover:border-medical-400 dark:hover:border-medical-500 transition-colors"
  >
    <span className="shrink-0 h-12 w-12 rounded-xl bg-medical-50 dark:bg-medical-900/40 flex items-center justify-center text-medical-600 dark:text-medical-300">
      <Icon className="h-6 w-6" />
    </span>
    <span className="min-w-0 flex-1">
      <span className="flex items-center gap-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
        {title}
        <ArrowRight className="h-4 w-4 text-medical-500 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
      </span>
      <span className="block text-sm text-slate-600 dark:text-slate-400 mt-1">{description}</span>
    </span>
  </Link>
);

const ReportStatusBadge: React.FC<{ report: Report }> = ({ report }) => {
  const { t } = useTranslation('common');
  const approved = report.is_approved;
  const cls = approved
    ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
    : report.status === 'FINAL'
      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
      : 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300';
  const label = approved
    ? t('dashboard.reportStatus.approved')
    : report.status === 'FINAL'
      ? t('dashboard.reportStatus.final')
      : t('dashboard.reportStatus.draft');
  return (
    <span className={`shrink-0 inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>
      {approved && <CheckCircle2 className="h-3 w-3" />}
      {label}
    </span>
  );
};

const Dashboard: React.FC = () => {
  const { t } = useTranslation('common');
  const navigate = useNavigate();

  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadReports = useCallback(async () => {
    const all = await apiClient.getReports();
    const sorted = [...all].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
    setReports(sorted.slice(0, RECENT_LIMIT));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      await loadReports();
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [loadReports]);

  useEffect(() => {
    load();
  }, [load]);

  // A completed analysis often produces a new report — refresh the list live so
  // it appears without a manual reload (best-effort; the REST fetch is canonical).
  const { lastMessage } = useWebSocket('/ws/monitor/tasks/');
  useEffect(() => {
    if (lastMessage?.type === 'task_completed') {
      loadReports().catch(() => {
        /* transient; next event or reload recovers */
      });
    }
  }, [lastMessage, loadReports]);

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <PageHeader
        icon={LayoutDashboard}
        title={t('dashboard.title')}
        subtitle={t('dashboard.subtitle')}
      />

      {/* Row 1 — quick-access tiles */}
        <div className="grid sm:grid-cols-2 gap-6 mb-6">
          <ActionTile
            to="/analyze?tab=new"
            icon={Zap}
            title={t('dashboard.quickAnalysis')}
            description={t('dashboard.quickAnalysisDesc')}
          />
          <ActionTile
            to="/analyze?tab=models"
            icon={Brain}
            title={t('dashboard.availableModels')}
            description={t('dashboard.availableModelsDesc')}
          />
        </div>

        {/* Row 2 — recent reports, full width */}
        <div className="medical-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <FileText className="h-5 w-5 text-medical-500" />
              {t('dashboard.recentReports')}
            </h2>
            <Link
              to="/analyze?tab=reports"
              className="inline-flex items-center gap-1 text-sm font-medium text-medical-600 dark:text-medical-400 hover:gap-2 transition-all"
            >
              {t('dashboard.viewAllReports')}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {loading ? (
            <div className="flex items-center gap-2 text-slate-400 py-8 justify-center">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : error ? (
            <div className="flex items-center justify-between py-4">
              <p className="text-slate-600 dark:text-slate-400">{t('dashboard.loadError')}</p>
              <button onClick={load} className="medical-button-primary">
                {t('dashboard.retry')}
              </button>
            </div>
          ) : reports.length === 0 ? (
            <div className="py-10 text-center">
              <FileText className="h-10 w-10 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-slate-600 dark:text-slate-400">{t('dashboard.noReports')}</p>
              <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">
                {t('dashboard.noReportsHint')}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500 border-b border-slate-200 dark:border-slate-700">
                    <th className="py-2 pr-4">{t('dashboard.reportTable.patientName')}</th>
                    <th className="py-2 pr-4">{t('dashboard.reportTable.patientId')}</th>
                    <th className="py-2 pr-4">{t('dashboard.reportTable.owner')}</th>
                    <th className="py-2 pr-4">{t('dashboard.reportTable.description')}</th>
                    <th className="py-2 pr-4">{t('dashboard.reportTable.date')}</th>
                    <th className="py-2">{t('dashboard.reportTable.status')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {reports.map((report) => {
                    const pi = report.patient_info ?? {};
                    const description =
                      pi.study_description && pi.study_description !== 'N/A'
                        ? pi.study_description
                        : report.title;
                    return (
                      <tr
                        key={report.id}
                        onClick={() => navigate(`/reports/${report.id}`)}
                        className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                      >
                        <td className="py-3 pr-4 font-medium text-slate-900 dark:text-slate-100 whitespace-nowrap">
                          <Link
                            to={`/reports/${report.id}`}
                            onClick={(e) => e.stopPropagation()}
                            className="hover:text-medical-600 dark:hover:text-medical-400"
                          >
                            {field(pi.patient_name)}
                          </Link>
                        </td>
                        <td className="py-3 pr-4 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                          {field(pi.patient_id)}
                        </td>
                        <td className="py-3 pr-4 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                          {field(pi.owner)}
                        </td>
                        <td className="py-3 pr-4 text-slate-600 dark:text-slate-400 max-w-[16rem] truncate">
                          {description}
                        </td>
                        <td className="py-3 pr-4 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                          {reportDate(report)}
                        </td>
                        <td className="py-3">
                          <ReportStatusBadge report={report} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
  );
};

export default Dashboard;
