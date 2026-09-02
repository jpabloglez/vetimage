/**
 * PlatformStatistics — live cross-clinic analysis activity.
 *
 * Computed on read rather than from a nightly rollup, so what you see is the
 * current state; the backend bounds the window to keep that affordable.
 *
 * This is the platform-wide view. A clinic's own figures are not here — each
 * clinic sees those on the Monitor page, scoped to them.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Loader2 } from 'lucide-react';

import { apiClient } from '../../utils/api';
import type { AdminClinic, AdminStatistics } from '../../types/api';
import Card, { CardContent, CardHeader, CardTitle } from '../ui/Card';

const WINDOWS = [7, 30, 90, 365];
const STATUSES = ['COMPLETED', 'FAILED', 'TIMEOUT', 'CANCELLED', 'PROCESSING', 'PENDING'];

interface Props {
  clinics: AdminClinic[];
}

export const PlatformStatistics: React.FC<Props> = ({ clinics }) => {
  const { t, i18n } = useTranslation('common');

  const [stats, setStats] = useState<AdminStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [clinic, setClinic] = useState<number | ''>('');
  const [model, setModel] = useState('');
  const [status, setStatus] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setStats(await apiClient.getAdminStatistics({
        days,
        clinic: clinic || undefined,
        model: model || undefined,
        status: status || undefined,
      }));
    } catch {
      toast.error(t('admin.stats.loadError'));
    } finally {
      setLoading(false);
    }
  }, [days, clinic, model, status, t]);

  useEffect(() => { void load(); }, [load]);

  // Model options come from the unfiltered response, so selecting one does not
  // remove the others from the list.
  const [modelOptions, setModelOptions] = useState<{ key: string; name: string }[]>([]);
  useEffect(() => {
    if (stats && !model && !status && !clinic) {
      setModelOptions(stats.by_model.map((m) => ({ key: m.model_key, name: m.name })));
    }
  }, [stats, model, status, clinic]);

  /**
   * The API returns only days that had activity. Plotting those directly would
   * space the axis by row rather than by date — three scattered days across a
   * month would render as three equal columns filling the width. Fill the
   * window so every day gets a slot and gaps read as gaps.
   */
  const series = useMemo(() => {
    if (!stats) return [];
    const byDay = new Map(stats.over_time.map((d) => [d.day, d]));
    const out: { day: string; total: number; succeeded: number; failed: number }[] = [];
    const cursor = new Date(stats.since);
    cursor.setHours(0, 0, 0, 0);
    const end = new Date();
    end.setHours(0, 0, 0, 0);
    while (cursor <= end) {
      const key = `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}-${String(cursor.getDate()).padStart(2, '0')}`;
      out.push(byDay.get(key) ?? { day: key, total: 0, succeeded: 0, failed: 0 });
      cursor.setDate(cursor.getDate() + 1);
    }
    return out;
  }, [stats]);

  const peak = useMemo(
    () => Math.max(1, ...series.map((d) => d.total)),
    [series],
  );

  const selectCls =
    'px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 ' +
    'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm ' +
    'focus:outline-none focus:ring-2 focus:ring-medical-500';

  const fmtDay = (iso: string) =>
    new Date(iso).toLocaleDateString(i18n.language, { day: 'numeric', month: 'short' });

  return (
    <div className="space-y-6">
      <Card variant="medical">
        <CardHeader>
          <CardTitle>{t('admin.stats.filters')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div>
              <label htmlFor="stat-days" className="block text-xs text-slate-500 mb-1">
                {t('admin.stats.window')}
              </label>
              <select
                id="stat-days" className={selectCls}
                value={days} onChange={(e) => setDays(Number(e.target.value))}
              >
                {WINDOWS.map((d) => (
                  <option key={d} value={d}>{t('admin.stats.lastDays', { count: d })}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="stat-clinic" className="block text-xs text-slate-500 mb-1">
                {t('admin.stats.clinic')}
              </label>
              <select
                id="stat-clinic" className={selectCls}
                value={clinic} onChange={(e) => setClinic(e.target.value ? Number(e.target.value) : '')}
              >
                <option value="">{t('admin.stats.allClinics')}</option>
                {clinics.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="stat-model" className="block text-xs text-slate-500 mb-1">
                {t('admin.stats.model')}
              </label>
              <select
                id="stat-model" className={selectCls}
                value={model} onChange={(e) => setModel(e.target.value)}
              >
                <option value="">{t('admin.stats.allModels')}</option>
                {modelOptions.map((m) => (
                  <option key={m.key} value={m.key}>{m.name || m.key}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="stat-status" className="block text-xs text-slate-500 mb-1">
                {t('admin.stats.status')}
              </label>
              <select
                id="stat-status" className={selectCls}
                value={status} onChange={(e) => setStatus(e.target.value)}
              >
                <option value="">{t('admin.stats.allStatuses')}</option>
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex justify-center py-16 text-slate-400">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      ) : !stats ? null : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: t('admin.stats.total'), value: stats.totals.total, tone: '' },
              { label: t('admin.stats.succeeded'), value: stats.totals.succeeded, tone: 'text-emerald-600 dark:text-emerald-400' },
              { label: t('admin.stats.failed'), value: stats.totals.failed, tone: 'text-red-600 dark:text-red-400' },
              {
                label: t('admin.stats.successRate'),
                value: stats.totals.success_rate === null ? '—' : `${stats.totals.success_rate}%`,
                tone: '',
              },
            ].map((kpi) => (
              <Card key={kpi.label} variant="medical">
                <CardContent className="py-5">
                  <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    {kpi.label}
                  </div>
                  <div className={`text-2xl font-semibold mt-1 tabular-nums ${kpi.tone}`}>
                    {kpi.value}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card variant="medical">
            <CardHeader>
              <CardTitle>{t('admin.stats.overTime')}</CardTitle>
            </CardHeader>
            <CardContent>
              {series.length === 0 || stats.totals.total === 0 ? (
                <p className="py-8 text-center text-sm text-slate-500">{t('admin.stats.noData')}</p>
              ) : (
                <div className="overflow-x-auto">
                  {/* items-stretch, not items-end: the bars size themselves as a
                        percentage of the column, which needs the column to fill the
                        track rather than shrink to its content. */}
                  <div className="flex items-stretch gap-1 h-40 min-w-full">
                    {series.map((d) => (
                      <div
                        key={d.day}
                        className="flex-1 min-w-[3px] h-full flex flex-col justify-end"
                        title={`${fmtDay(d.day)}: ${d.total} (${d.succeeded} ok, ${d.failed} failed)`}
                      >
                        {d.failed > 0 && (
                          <div
                            className="bg-red-400 dark:bg-red-500 rounded-t-sm"
                            style={{ height: `${(d.failed / peak) * 100}%` }}
                          />
                        )}
                        <div
                          className="bg-medical-500 dark:bg-medical-400"
                          style={{ height: `${(d.succeeded / peak) * 100}%` }}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-between text-xs text-slate-400 mt-2">
                    <span>{fmtDay(series[0].day)}</span>
                    <span>{fmtDay(series[series.length - 1].day)}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card variant="medical">
              <CardHeader>
                <CardTitle>{t('admin.stats.byModel')}</CardTitle>
              </CardHeader>
              <CardContent>
                {stats.by_model.length === 0 ? (
                  <p className="py-6 text-center text-sm text-slate-500">{t('admin.stats.noData')}</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs uppercase tracking-wide text-slate-500 border-b border-slate-200 dark:border-slate-700">
                        <th className="py-2 pr-4 font-medium">{t('admin.stats.model')}</th>
                        <th className="py-2 pr-4 font-medium text-right">{t('admin.stats.total')}</th>
                        <th className="py-2 pr-4 font-medium text-right">{t('admin.stats.succeeded')}</th>
                        <th className="py-2 font-medium text-right">{t('admin.stats.failed')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {stats.by_model.map((m) => (
                        <tr key={m.model_key}>
                          <td className="py-2.5 pr-4">
                            <div className="text-slate-900 dark:text-slate-100">{m.name || m.model_key}</div>
                            <div className="text-xs text-slate-400 font-mono">{m.model_key}</div>
                          </td>
                          <td className="py-2.5 pr-4 text-right tabular-nums">{m.total}</td>
                          <td className="py-2.5 pr-4 text-right tabular-nums text-emerald-600 dark:text-emerald-400">{m.succeeded}</td>
                          <td className="py-2.5 text-right tabular-nums text-red-600 dark:text-red-400">{m.failed}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </CardContent>
            </Card>

            <Card variant="medical">
              <CardHeader>
                <CardTitle>{t('admin.stats.byClinic')}</CardTitle>
              </CardHeader>
              <CardContent>
                {stats.by_clinic.length === 0 ? (
                  <p className="py-6 text-center text-sm text-slate-500">{t('admin.stats.noData')}</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs uppercase tracking-wide text-slate-500 border-b border-slate-200 dark:border-slate-700">
                        <th className="py-2 pr-4 font-medium">{t('admin.stats.clinic')}</th>
                        <th className="py-2 font-medium text-right">{t('admin.stats.analyses')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {stats.by_clinic.map((c) => (
                        <tr key={c.clinic_id ?? 'none'}>
                          <td className="py-2.5 pr-4">{c.name ?? '—'}</td>
                          <td className="py-2.5 text-right tabular-nums">{c.total}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
};

export default PlatformStatistics;
