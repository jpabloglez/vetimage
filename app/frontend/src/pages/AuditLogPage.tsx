/**
 * AuditLogPage — clinic-admin view of the authentication/authorization audit
 * trail (who accessed what, when, from where). Admins see the whole
 * organization; the backend scopes non-admins to their own events.
 *
 * Supports the data-security goal: visibility + accountability for owner data
 * access. Filter by event type, suspicious-only, and date range.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Shield, AlertTriangle, RefreshCw } from 'lucide-react';
import { apiClient, type AuditLogEntry } from '../utils/api';
import { Card, CardContent } from '../components/ui';

const EVENT_TYPES = [
  'login_success', 'login_failed', 'logout', 'token_refresh', 'token_expired',
  'password_change', 'password_reset_request', 'password_reset_complete',
  'apikey_auth', 'apikey_created', 'apikey_revoked',
  'session_created', 'session_terminated',
  'suspicious_activity', 'rate_limit_exceeded', 'invalid_token', 'scope_violation',
];

const AuditLogPage: React.FC = () => {
  const { t } = useTranslation('common');
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [eventType, setEventType] = useState('');
  const [suspiciousOnly, setSuspiciousOnly] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setLogs(await apiClient.getAuditLogs({
        event_type: eventType || undefined,
        suspicious_only: suspiciousOnly || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      }));
    } catch {
      toast.error(t('audit.loadError', 'Failed to load audit log'));
    } finally {
      setLoading(false);
    }
  }, [eventType, suspiciousOnly, startDate, endDate, t]);

  useEffect(() => { load(); }, [load]);

  const selectClass =
    'px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-medical-500';

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-medical-500 to-teal-500 flex items-center justify-center">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{t('auditLog.title', 'Audit Log')}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t('auditLog.subtitle', 'Authentication & access events for your clinic')}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3 mb-5">
        <div>
          <label htmlFor="audit-event" className="block text-xs text-slate-500 mb-1">{t('auditLog.eventType', 'Event type')}</label>
          <select id="audit-event" className={selectClass} value={eventType} onChange={(e) => setEventType(e.target.value)}>
            <option value="">{t('auditLog.allEvents', 'All events')}</option>
            {EVENT_TYPES.map((et) => <option key={et} value={et}>{et}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="audit-from" className="block text-xs text-slate-500 mb-1">{t('auditLog.from', 'From')}</label>
          <input id="audit-from" type="date" className={selectClass} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </div>
        <div>
          <label htmlFor="audit-to" className="block text-xs text-slate-500 mb-1">{t('auditLog.to', 'To')}</label>
          <input id="audit-to" type="date" className={selectClass} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 pb-2">
          <input type="checkbox" checked={suspiciousOnly} onChange={(e) => setSuspiciousOnly(e.target.checked)} />
          {t('auditLog.suspiciousOnly', 'Suspicious only')}
        </label>
        <button
          onClick={load}
          className="flex items-center gap-1.5 px-3 py-2 rounded-medical border border-slate-300 dark:border-slate-600 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          <RefreshCw className="w-4 h-4" /> {t('buttons.refresh', 'Refresh')}
        </button>
      </div>

      {loading ? (
        <p className="text-slate-500">{t('buttons.loading', 'Loading...')}</p>
      ) : logs.length === 0 ? (
        <Card><CardContent className="py-12 text-center text-slate-500">
          {t('auditLog.empty', 'No audit events match these filters.')}
        </CardContent></Card>
      ) : (
        <div className="overflow-x-auto border border-slate-200 dark:border-slate-700 rounded-medical">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">{t('auditLog.when', 'When')}</th>
                <th className="px-4 py-2">{t('auditLog.user', 'User')}</th>
                <th className="px-4 py-2">{t('auditLog.event', 'Event')}</th>
                <th className="px-4 py-2">{t('auditLog.ip', 'IP')}</th>
                <th className="px-4 py-2">{t('auditLog.path', 'Path')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {logs.map((l) => (
                <tr key={l.id} className={l.is_suspicious ? 'bg-amber-50 dark:bg-amber-950/20' : ''}>
                  <td className="px-4 py-2 whitespace-nowrap text-slate-600 dark:text-slate-400">
                    {new Date(l.event_timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-slate-800 dark:text-slate-100">{l.user_email || l.username_attempted || '—'}</td>
                  <td className="px-4 py-2">
                    <span className="inline-flex items-center gap-1">
                      {l.is_suspicious && <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />}
                      {l.event_type_display}
                    </span>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-slate-500">{l.ip_address}</td>
                  <td className="px-4 py-2 text-slate-500 truncate max-w-[200px]" title={l.request_path}>
                    {l.request_method} {l.request_path}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default AuditLogPage;
