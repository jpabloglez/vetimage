/**
 * Comparison Selector
 *
 * Dropdowns to select two reports for side-by-side comparison.
 */

import React from 'react';
import type { Report } from '../../utils/api';

interface ComparisonSelectorProps {
  reports: Report[];
  reportA: string | null;
  reportB: string | null;
  onSelectA: (id: string) => void;
  onSelectB: (id: string) => void;
}

const ComparisonSelector: React.FC<ComparisonSelectorProps> = ({
  reports,
  reportA,
  reportB,
  onSelectA,
  onSelectB,
}) => {
  return (
    <div className="grid md:grid-cols-2 gap-4 mb-6">
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
          Report A
        </label>
        <select
          value={reportA || ''}
          onChange={(e) => onSelectA(e.target.value)}
          className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-sm"
        >
          <option value="">Select report...</option>
          {reports.map(r => (
            <option key={r.id} value={r.id} disabled={r.id === reportB}>
              {r.title} ({new Date(r.created_at).toLocaleDateString()})
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
          Report B
        </label>
        <select
          value={reportB || ''}
          onChange={(e) => onSelectB(e.target.value)}
          className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-sm"
        >
          <option value="">Select report...</option>
          {reports.map(r => (
            <option key={r.id} value={r.id} disabled={r.id === reportA}>
              {r.title} ({new Date(r.created_at).toLocaleDateString()})
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default ComparisonSelector;
