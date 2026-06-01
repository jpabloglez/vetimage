/**
 * Audit Report Filters
 *
 * Date range, user, event type filtering for audit reports.
 */

import React from 'react';

export interface AuditFilters {
  date_from?: string;
  date_to?: string;
  event_type?: string;
  risk_score_min?: number;
}

const EVENT_TYPES = [
  'login_success', 'login_failed', 'logout',
  'token_refresh', 'token_expired',
  'password_change', 'password_reset_request',
  'apikey_auth', 'apikey_created', 'apikey_revoked',
  'session_created', 'session_terminated',
  'suspicious_activity', 'rate_limit_exceeded',
  'scope_violation',
];

interface AuditReportFiltersProps {
  filters: AuditFilters;
  onChange: (filters: AuditFilters) => void;
}

const AuditReportFilters: React.FC<AuditReportFiltersProps> = ({ filters, onChange }) => {
  const update = (key: keyof AuditFilters, value: any) => {
    onChange({ ...filters, [key]: value || undefined });
  };

  return (
    <div className="grid md:grid-cols-4 gap-4">
      <div>
        <label className="block text-sm font-medium mb-1">From</label>
        <input
          type="date"
          value={filters.date_from?.split('T')[0] || ''}
          onChange={(e) => update('date_from', e.target.value ? `${e.target.value}T00:00:00Z` : undefined)}
          className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-sm"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">To</label>
        <input
          type="date"
          value={filters.date_to?.split('T')[0] || ''}
          onChange={(e) => update('date_to', e.target.value ? `${e.target.value}T23:59:59Z` : undefined)}
          className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-sm"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Event Type</label>
        <select
          value={filters.event_type || ''}
          onChange={(e) => update('event_type', e.target.value)}
          className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-sm"
        >
          <option value="">All events</option>
          {EVENT_TYPES.map(et => (
            <option key={et} value={et}>{et.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Min Risk Score</label>
        <input
          type="number"
          min={0}
          max={100}
          value={filters.risk_score_min ?? ''}
          onChange={(e) => update('risk_score_min', e.target.value ? Number(e.target.value) : undefined)}
          placeholder="0"
          className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-sm"
        />
      </div>
    </div>
  );
};

export default AuditReportFilters;
