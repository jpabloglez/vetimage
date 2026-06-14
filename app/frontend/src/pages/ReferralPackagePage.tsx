/**
 * ReferralPackagePage — public, read-only referral bundle for a receiving vet.
 *
 * Reached via an unguessable link (/referral/:token) the referring clinic sends
 * to a specialist. No login required. Shows the patient signalment, the reason
 * for referral, a history summary, the linked report findings, and a pointer to
 * the shared study. Framed as decision-support, not a diagnosis.
 */
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { PawPrint, Stethoscope, FileText, AlertTriangle } from 'lucide-react';
import { apiClient, type PublicReferralPackage, type ReferralUrgency } from '../utils/api';

const URGENCY_CLS: Record<ReferralUrgency, string> = {
  routine: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200',
  urgent: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
  emergency: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200',
};

const ReferralPackagePage: React.FC = () => {
  const { t } = useTranslation('patients');
  const { token } = useParams<{ token: string }>();
  const [pkg, setPkg] = useState<PublicReferralPackage | null>(null);
  const [state, setState] = useState<'loading' | 'ok' | 'error'>('loading');

  useEffect(() => {
    if (!token) { setState('error'); return; }
    apiClient.getPublicReferral(token)
      .then((p) => { setPkg(p); setState('ok'); })
      .catch(() => setState('error'));
  }, [token]);

  if (state === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-medical-500" />
      </div>
    );
  }

  if (state === 'error' || !pkg) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 px-4">
        <div className="text-center max-w-md">
          <PawPrint className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-slate-900 dark:text-white mb-2">{t('referralPage.notAvailableTitle')}</h1>
          <p className="text-slate-500 dark:text-slate-400">{t('referralPage.notAvailableBody')}</p>
        </div>
      </div>
    );
  }

  const signalment = ([
    ['name', pkg.patient.name],
    ['species', pkg.patient.species],
    ['breed', pkg.patient.breed],
    ['sex', pkg.patient.sex],
    ['date_of_birth', pkg.patient.date_of_birth ?? ''],
    ['microchip_id', pkg.patient.microchip_id],
  ] as Array<[string, string]>).filter(([, v]) => v);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div className="max-w-2xl mx-auto px-4 h-16 flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-medical-500 to-teal-500 flex items-center justify-center">
            <PawPrint className="w-4 h-4 text-white" />
          </div>
          <span className="text-lg font-bold text-slate-900 dark:text-white">VetImage</span>
          {pkg.referring_clinic_name && (
            <span className="ml-auto text-sm text-slate-500">{pkg.referring_clinic_name}</span>
          )}
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center gap-3">
          <Stethoscope className="w-6 h-6 text-medical-600 dark:text-medical-400" />
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{t('referralPage.title')}</h1>
          <span className={`ml-auto px-2.5 py-1 rounded-full text-xs font-semibold ${URGENCY_CLS[pkg.urgency]}`}>
            {t(`referral.urgencies.${pkg.urgency}`)}
          </span>
        </div>

        {/* Signalment */}
        <section className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-3 flex items-center gap-2">
            <PawPrint className="w-4 h-4 text-medical-500" /> {t('referralPage.patient')}
          </h2>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            {signalment.map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs uppercase tracking-wide text-slate-400">{t(`referralPage.fields.${k}`)}</dt>
                <dd className="font-medium text-slate-800 dark:text-slate-100">{v}</dd>
              </div>
            ))}
          </dl>
        </section>

        {/* Reason + history */}
        {(pkg.reason || pkg.history_summary) && (
          <section className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 space-y-4">
            {pkg.reason && (
              <div>
                <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-1">{t('referralPage.reason')}</h2>
                <p className="text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-line">{pkg.reason}</p>
              </div>
            )}
            {pkg.history_summary && (
              <div>
                <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-1">{t('referralPage.history')}</h2>
                <p className="text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-line">{pkg.history_summary}</p>
              </div>
            )}
          </section>
        )}

        {/* Report findings */}
        {pkg.report && (
          <section className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-3 flex items-center gap-2">
              <FileText className="w-4 h-4 text-medical-500" /> {pkg.report.title}
            </h2>
            {pkg.report.findings.length > 0 && (
              <ul className="space-y-2 mb-3">
                {pkg.report.findings.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-slate-700 dark:text-slate-300">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-medical-500 flex-shrink-0" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            )}
            {pkg.report.summary && (
              <p className="text-slate-700 dark:text-slate-300 leading-relaxed">{pkg.report.summary}</p>
            )}
          </section>
        )}

        {/* Study pointer */}
        {pkg.study_instance_uid && (
          <section className="flex items-start gap-3 rounded-xl border border-medical-200 dark:border-medical-800 bg-medical-50 dark:bg-medical-950/20 px-4 py-3">
            <FileText className="w-5 h-5 text-medical-600 dark:text-medical-400 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-medical-900 dark:text-medical-200">
              <p className="font-medium">{t('referralPage.studyAttached')}</p>
              <p className="font-mono text-xs text-medical-700 dark:text-medical-300 break-all">{pkg.study_instance_uid}</p>
            </div>
          </section>
        )}

        {/* Disclaimer */}
        <div className="flex items-start gap-2 text-xs text-slate-400 leading-relaxed">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <p>{pkg.disclaimer}</p>
        </div>
      </main>
    </div>
  );
};

export default ReferralPackagePage;
