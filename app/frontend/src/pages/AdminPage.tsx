/**
 * Admin Page — VetImage platform staff only.
 *
 * The one area that reads across every clinic, so access is gated on
 * `is_staff` (not on the clinical `role` field) both here and on the server,
 * via core.permissions.IsPlatformStaff. The route guard is a courtesy for
 * navigation — the backend refuses non-staff regardless.
 *
 * What it shows is deliberately aggregate: counts, timestamps and clinic
 * names, never patient names, findings or images. A platform admin counts
 * studies; they do not read them.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ShieldCheck } from 'lucide-react';

import PageHeader from '../components/ui/PageHeader';
import Card, { CardContent } from '../components/ui/Card';
import ClinicRegistry from '../components/admin/ClinicRegistry';
import PlatformStatistics from '../components/admin/PlatformStatistics';
import { apiClient } from '../utils/api';
import type { AdminClinic, AdminPlatformSummary } from '../types/api';

type TabType = 'clinics' | 'statistics';

const AdminPage: React.FC = () => {
  const { t } = useTranslation('common');
  const [activeTab, setActiveTab] = useState<TabType>('clinics');
  const [summary, setSummary] = useState<AdminPlatformSummary | null>(null);
  const [clinics, setClinics] = useState<AdminClinic[]>([]);

  useEffect(() => {
    let cancelled = false;
    // Failures are silent here: the headline strip is context, not the page.
    // Each panel reports its own errors.
    apiClient.getAdminSummary()
      .then((s) => !cancelled && setSummary(s))
      .catch(() => undefined);
    apiClient.getAdminClinics()
      .then((c) => !cancelled && setClinics(c))
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, []);

  const kpis = summary
    ? [
        { label: t('admin.summary.clinics'), value: summary.clinics },
        { label: t('admin.summary.users'), value: summary.users },
        { label: t('admin.summary.patients'), value: summary.patients },
        { label: t('admin.summary.studies'), value: summary.studies },
        { label: t('admin.summary.analyses30d'), value: summary.analyses_last_30d },
        { label: t('admin.summary.pendingInvitations'), value: summary.pending_invitations },
      ]
    : [];

  const tabs: { key: TabType; label: string }[] = [
    { key: 'clinics', label: t('admin.tabs.clinics') },
    { key: 'statistics', label: t('admin.tabs.statistics') },
  ];

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <PageHeader icon={ShieldCheck} title={t('admin.title')} subtitle={t('admin.subtitle')} />

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
          {kpis.map((kpi) => (
            <Card key={kpi.label} variant="medical">
              <CardContent className="py-4">
                <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  {kpi.label}
                </div>
                <div className="text-xl font-semibold mt-1 tabular-nums">{kpi.value}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="mb-6 border-b border-slate-200 dark:border-slate-700">
        <nav className="flex gap-8">
          {tabs.map((tab) => (
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

      {activeTab === 'clinics' && <ClinicRegistry />}
      {activeTab === 'statistics' && <PlatformStatistics clinics={clinics} />}
    </div>
  );
};

export default AdminPage;
