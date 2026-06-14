/**
 * OwnerReportPage — public, read-only, plain-language view of a pet's report.
 *
 * Reached via an unguessable share link (/shared/:token) the clinic sends to the
 * owner. No login required. Only APPROVED reports are ever served here, and the
 * framing is explicit: results were reviewed by the veterinarian and are not an
 * AI verdict. See docs/VETERINARY_ALIGNMENT_REPORT.md (Phase 7).
 */
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { PawPrint, CheckCircle2, Stethoscope } from 'lucide-react';
import { apiClient, type PublicSharedReport } from '../utils/api';

const SIGNALMENT_KEYS = [
  'patient_name', 'species', 'breed', 'sex',
  'date_of_birth', 'weight', 'owner', 'study_date', 'study_description',
];

const OwnerReportPage: React.FC = () => {
  const { t } = useTranslation('patients');
  const { token } = useParams<{ token: string }>();
  const [report, setReport] = useState<PublicSharedReport | null>(null);
  const [state, setState] = useState<'loading' | 'ok' | 'error'>('loading');

  useEffect(() => {
    if (!token) { setState('error'); return; }
    apiClient.getSharedReport(token)
      .then((r) => { setReport(r); setState('ok'); })
      .catch(() => setState('error'));
  }, [token]);

  if (state === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-medical-500" />
      </div>
    );
  }

  if (state === 'error' || !report) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 px-4">
        <div className="text-center max-w-md">
          <PawPrint className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-slate-900 dark:text-white mb-2">{t('ownerReport.notAvailableTitle')}</h1>
          <p className="text-slate-500 dark:text-slate-400">
            {t('ownerReport.notAvailableBody')}
          </p>
        </div>
      </div>
    );
  }

  const signalment = SIGNALMENT_KEYS
    .filter((k) => (report.patient_info || {})[k])
    .map((k) => [k, (report.patient_info as Record<string, string>)[k]] as const);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div className="max-w-2xl mx-auto px-4 h-16 flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-medical-500 to-teal-500 flex items-center justify-center">
            <PawPrint className="w-4 h-4 text-white" />
          </div>
          <span className="text-lg font-bold text-slate-900 dark:text-white">VetImage</span>
          {report.clinic && <span className="ml-auto text-sm text-slate-500">{report.clinic}</span>}
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* Vet-reviewed banner */}
        <div className="flex items-start gap-3 rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/20 px-4 py-3">
          <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-semibold text-green-900 dark:text-green-100">{t('ownerReport.reviewedTitle')}</p>
            <p className="text-sm text-green-800 dark:text-green-300">
              {report.approved_at
                ? t('ownerReport.approvedOn', { date: new Date(report.approved_at).toLocaleDateString() })
                : t('ownerReport.approvedByClinic')}{' '}{t('ownerReport.reviewedBody')}
            </p>
          </div>
        </div>

        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{report.title}</h1>

        {/* Signalment */}
        {signalment.length > 0 && (
          <section className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-3 flex items-center gap-2">
              <PawPrint className="w-4 h-4 text-medical-500" /> {t('ownerReport.yourPet')}
            </h2>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              {signalment.map(([k, v]) => (
                <div key={k}>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">{t(`ownerReport.fields.${k}`)}</dt>
                  <dd className="font-medium text-slate-800 dark:text-slate-100">{v}</dd>
                </div>
              ))}
            </dl>
          </section>
        )}

        {/* Findings */}
        <section className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-3">{t('ownerReport.whatWeLooked')}</h2>
          {report.findings.length > 0 ? (
            <ul className="space-y-2">
              {report.findings.map((f, i) => (
                <li key={i} className="flex items-start gap-2 text-slate-700 dark:text-slate-300">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-medical-500 flex-shrink-0" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 dark:text-slate-400">{t('ownerReport.noFindings')}</p>
          )}
          {report.summary && (
            <p className="mt-4 text-slate-700 dark:text-slate-300 leading-relaxed">{report.summary}</p>
          )}
        </section>

        {/* Talk to your vet */}
        <section className="flex items-start gap-3 rounded-xl border border-medical-200 dark:border-medical-800 bg-medical-50 dark:bg-medical-950/20 px-4 py-3">
          <Stethoscope className="w-5 h-5 text-medical-600 dark:text-medical-400 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-medical-900 dark:text-medical-200">
            {t('ownerReport.talkToVet')}
          </p>
        </section>

        {/* Disclaimer */}
        <p className="text-xs text-slate-400 leading-relaxed">{report.disclaimer}</p>
      </main>
    </div>
  );
};

export default OwnerReportPage;
