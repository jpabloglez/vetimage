/**
 * Reports Page
 *
 * Lists generated reports with ability to create new ones from
 * completed analysis tasks and download PDFs.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { FileText, Download, Plus, ChevronDown, ChevronUp, RefreshCw, GitCompare } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { apiClient, type Report, type AnalysisTask } from '../utils/api';
import ReportViewer from '../components/reports/ReportViewer';
import GenerateReportModal from '../components/reports/GenerateReportModal';
import ComparisonSelector from '../components/reports/ComparisonSelector';
import ReportComparison from '../components/reports/ReportComparison';

const ReportsPage: React.FC = () => {
  const { t } = useTranslation('reports');
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [compareA, setCompareA] = useState<string | null>(null);
  const [compareB, setCompareB] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.getReports();
      setReports(data);
    } catch {
      toast.error(t('common:errors.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleDownloadPdf = async (reportId: string) => {
    try {
      setDownloading(reportId);
      await apiClient.downloadReportPdf(reportId);
    } catch {
      toast.error(t('downloadError'));
    } finally {
      setDownloading(null);
    }
  };

  const handleReportCreated = () => {
    setShowModal(false);
    fetchReports();
    toast.success(t('generateSuccess'));
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 pt-20">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold medical-gradient-text mb-2">{t('title')}</h1>
            <p className="text-slate-600 dark:text-slate-400">
              {t('subtitle')}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={fetchReports}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              {t('refresh')}
            </button>
            <button
              onClick={() => { setCompareMode(!compareMode); setCompareA(null); setCompareB(null); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                compareMode
                  ? 'border-medical-500 text-medical-600 bg-medical-50 dark:bg-medical-950/20'
                  : 'border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              <GitCompare className="w-4 h-4" />
              {t('compare')}
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-medical-600 text-white hover:bg-medical-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              {t('generate')}
            </button>
          </div>
        </div>

        {/* Comparison Mode */}
        {compareMode && (
          <div className="mb-6">
            <ComparisonSelector
              reports={reports}
              reportA={compareA}
              reportB={compareB}
              onSelectA={setCompareA}
              onSelectB={setCompareB}
            />
            {compareA && compareB && (
              <ReportComparison
                reportA={reports.find(r => r.id === compareA)!}
                reportB={reports.find(r => r.id === compareB)!}
              />
            )}
          </div>
        )}

        {/* Report Table */}
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-medical-600" />
          </div>
        ) : reports.length === 0 ? (
          <div className="medical-card p-12 text-center">
            <FileText className="w-12 h-12 text-slate-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              {t('noReports')}
            </h3>
            <p className="text-slate-600 dark:text-slate-400 mb-4">
              {t('noReportsHint')}
            </p>
            <button
              onClick={() => setShowModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-medical-600 text-white hover:bg-medical-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              {t('generate')}
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {reports.map((report) => (
              <div key={report.id} className="medical-card overflow-hidden">
                {/* Row */}
                <div className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <FileText className="w-5 h-5 text-medical-600 dark:text-medical-400 flex-shrink-0" />
                    <div className="min-w-0">
                      <h3 className="font-medium text-slate-900 dark:text-slate-100 truncate">
                        {report.title}
                      </h3>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        {report.model_name} &middot;{' '}
                        {new Date(report.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        report.status === 'FINAL'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                      }`}
                    >
                      {report.status}
                    </span>

                    <button
                      onClick={() => handleDownloadPdf(report.id)}
                      disabled={downloading === report.id}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
                    >
                      <Download className="w-3.5 h-3.5" />
                      {t('downloadPdf')}
                    </button>

                    <button
                      onClick={() =>
                        setExpandedId(expandedId === report.id ? null : report.id)
                      }
                      className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                    >
                      {expandedId === report.id ? (
                        <ChevronUp className="w-4 h-4 text-slate-500" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-slate-500" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Expanded content */}
                {expandedId === report.id && report.content && (
                  <div className="border-t border-slate-200 dark:border-slate-700 p-4">
                    <ReportViewer content={report.content} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Generate Report Modal */}
        {showModal && (
          <GenerateReportModal
            onClose={() => setShowModal(false)}
            onCreated={handleReportCreated}
          />
        )}
      </div>
    </div>
  );
};

export default ReportsPage;
