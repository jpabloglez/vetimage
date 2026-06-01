/**
 * User Activity Table
 *
 * Sortable table showing per-user activity stats (admin only).
 */

import React, { useState } from 'react';
import { ArrowUpDown } from 'lucide-react';
import { formatFileSize, type UserActivity } from '../../utils/api';

interface UserActivityTableProps {
  data: UserActivity[];
}

type SortKey = 'email' | 'upload_count' | 'analysis_count' | 'total_storage_bytes';

export const UserActivityTable: React.FC<UserActivityTableProps> = ({ data }) => {
  const [sortKey, setSortKey] = useState<SortKey>('analysis_count');
  const [sortAsc, setSortAsc] = useState(false);

  if (!data || data.length === 0) return null;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const sorted = [...data].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }
    return sortAsc ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
  });

  const SortHeader: React.FC<{ label: string; field: SortKey }> = ({ label, field }) => (
    <th
      className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300 cursor-pointer hover:text-medical-600 dark:hover:text-medical-400"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        <ArrowUpDown className="w-3 h-3" />
      </div>
    </th>
  );

  return (
    <div className="medical-card p-6">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
        User Activity
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-50 dark:bg-slate-800">
            <tr>
              <SortHeader label="User" field="email" />
              <SortHeader label="Uploads" field="upload_count" />
              <SortHeader label="Analyses" field="analysis_count" />
              <SortHeader label="Storage" field="total_storage_bytes" />
              <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">
                Last Active
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {sorted.map((user) => (
              <tr key={user.user_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                <td className="py-3 px-4 text-sm text-slate-900 dark:text-white">
                  {user.email}
                </td>
                <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                  {user.upload_count}
                </td>
                <td className="py-3 px-4 text-sm">
                  <span className="text-slate-900 dark:text-white">{user.analysis_count}</span>
                  {user.analysis_count > 0 && (
                    <span className="text-xs text-slate-500 ml-1">
                      ({user.completed_analyses} OK / {user.failed_analyses} fail)
                    </span>
                  )}
                </td>
                <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                  {formatFileSize(user.total_storage_bytes)}
                </td>
                <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                  {user.last_active_at
                    ? new Date(user.last_active_at).toLocaleDateString()
                    : 'Never'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default UserActivityTable;
