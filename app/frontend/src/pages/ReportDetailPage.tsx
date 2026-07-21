import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import {
  AlertCircle,
  ArrowLeft,
  Brain,
  CheckCircle2,
  Download,
  FileText,
  Loader2,
} from 'lucide-react';

import { apiClient } from '../utils/api';
import type { AnalysisTask, Finding, Report, ReportPatientInfo } from '../types/api';

/** Normalize the DICOM/report placeholder "N/A" (and empty values) to an em-dash. */
const field = (value?: string): string => (value && value !== 'N/A' ? value : '—');

/** A single label/value row inside the analysis-detail table. */
const Row: React.FC<{ label: string; value?: React.ReactNode }> = ({ label, value }) => (
  <tr>
    <th
      scope="row"
      className="py-2 pr-6 text-left font-normal text-slate-500 dark:text-slate-400 whitespace-nowrap align-top w-px"
    >
      {label}
    </th>
    <td className="py-2 font-medium text-slate-900 dark:text-slate-100 break-words">
      {value ?? '—'}
    </td>
  </tr>
);

const ReportDetailPage: React.FC = () => {
  const { t } = useTranslation('reports');
  const { id } = useParams<{ id: string }>();

  const [report, setReport] = useState<Report | null>(null);
  const [task, setTask] = useState<AnalysisTask | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!id) return;
    let objectUrl: string | null = null;
    let cancelled = false;

    (async () => {
      setLoading(true);
      setError(false);
      try {
        const rpt = await apiClient.getReport(id);
        if (cancelled) return;
        setReport(rpt);

        // Related analysis details are best-effort — a report may be authored
        // without a linked task, so a failure here shouldn't blank the page.
        if (rpt.analysis_task_id) {
          apiClient
            .getAnalysisTask(rpt.analysis_task_id)
            .then((tk) => !cancelled && setTask(tk))
            .catch(() => undefined);
        }

        objectUrl = await apiClient.getReportPdfObjectUrl(id);
        if (cancelled) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        setPdfUrl(objectUrl);
      } catch {
        if (!cancelled) setError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [id]);

  const handleDownload = useCallback(async () => {
    if (!id) return;
    try {
      setDownloading(true);
      await apiClient.downloadReportPdf(id);
    } catch {
      toast.error(t('downloadError'));
    } finally {
      setDownloading(false);
    }
  }, [id, t]);

  const findings: Finding[] = Array.isArray(task?.result_metadata?.findings)
    ? (task!.result_metadata!.findings as Finding[])
    : [];

  const patient: ReportPatientInfo =
    report?.patient_info ?? (report?.content?.patient_info as ReportPatientInfo) ?? {};

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 pt-20">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1 text-sm font-medium text-medical-600 dark:text-medical-400 hover:gap-2 transition-all mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('detail.backToDashboard')}
        </Link>

        {loading ? (
          <div className="flex items-center justify-center py-24 text-slate-400">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : error || !report ? (
          <div className="medical-card p-12 text-center">
            <AlertCircle className="h-10 w-10 text-red-400 mx-auto mb-3" />
            <p className="text-slate-600 dark:text-slate-400">{t('detail.loadError')}</p>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
              <div className="min-w-0">
                <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <FileText className="h-6 w-6 text-medical-500 shrink-0" />
                  <span className="truncate">{report.title}</span>
                </h1>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  {report.model_name}
                  {report.model_name && ' · '}
                  {new Date(report.created_at).toLocaleString()}
                </p>
              </div>
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="medical-button-primary inline-flex items-center gap-2 disabled:opacity-60"
              >
                {downloading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                {t('downloadPdf')}
              </button>
            </div>

            <div className="space-y-6">
              {/* Analysis detail — table format, above the embedded viewer */}
              <div className="medical-card p-6">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Brain className="h-5 w-5 text-medical-500" />
                  {t('detail.analysisInfo')}
                </h2>
                <div className="overflow-x-auto">
                  <table className="text-sm">
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      <Row label={t('detail.patientName')} value={field(patient.patient_name)} />
                      <Row label={t('detail.patientId')} value={field(patient.patient_id)} />
                      <Row label={t('detail.owner')} value={field(patient.owner)} />
                      <Row label={t('detail.model')} value={report.model_name} />
                      {task && (
                        <>
                          <Row label={t('detail.status')} value={task.status} />
                          {task.priority && (
                            <Row label={t('detail.priority')} value={task.priority} />
                          )}
                          {typeof task.processing_duration === 'number' && (
                            <Row
                              label={t('detail.duration')}
                              value={`${task.processing_duration.toFixed(1)}s`}
                            />
                          )}
                          {task.completed_at && (
                            <Row
                              label={t('detail.completedAt')}
                              value={new Date(task.completed_at).toLocaleString()}
                            />
                          )}
                        </>
                      )}
                      <Row
                        label={t('detail.reportStatus')}
                        value={
                          report.is_approved ? (
                            <span className="inline-flex items-center gap-1 text-green-600 dark:text-green-400">
                              <CheckCircle2 className="h-4 w-4" />
                              {t('detail.approved')}
                            </span>
                          ) : (
                            report.status
                          )
                        }
                      />
                      {report.study_uid && (
                        <Row
                          label={t('detail.studyUid')}
                          value={<span className="font-mono text-xs">{report.study_uid}</span>}
                        />
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {findings.length > 0 && (
                <div className="medical-card p-6">
                  <h2 className="text-lg font-semibold mb-3">{t('detail.findings')}</h2>
                  <ul className="space-y-2">
                    {findings.map((f, i) => (
                      <li
                        key={i}
                        className="flex items-center justify-between gap-2 text-sm py-1.5 border-b border-slate-100 dark:border-slate-800 last:border-0"
                      >
                        <span className="min-w-0">
                          <span className="font-medium text-slate-900 dark:text-slate-100">
                            {f.label ?? '—'}
                          </span>
                          {f.region && (
                            <span className="text-slate-400 dark:text-slate-500"> · {f.region}</span>
                          )}
                        </span>
                        {typeof f.confidence === 'number' && (
                          <span className="shrink-0 text-slate-500 dark:text-slate-400">
                            {Math.round(f.confidence * 100)}%
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-3">
                    {t('detail.aiDisclaimer')}
                  </p>
                </div>
              )}

              {/* Embedded PDF viewer */}
              <div className="medical-card overflow-hidden">
                {pdfUrl ? (
                  <iframe title={report.title} src={pdfUrl} className="w-full h-[85vh] bg-white" />
                ) : (
                  <div className="flex flex-col items-center justify-center h-[60vh] text-slate-400">
                    <AlertCircle className="h-8 w-8 mb-2" />
                    <p className="text-sm">{t('detail.pdfUnavailable')}</p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ReportDetailPage;
