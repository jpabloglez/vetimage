/**
 * My Activity Card
 *
 * Displays current user's personal activity metrics.
 */

import React from 'react';
import { Upload, Brain, HardDrive, Clock } from 'lucide-react';
import { formatFileSize, type UserActivity } from '../../utils/api';

interface MyActivityCardProps {
  data: UserActivity | null;
}

export const MyActivityCard: React.FC<MyActivityCardProps> = ({ data }) => {
  if (!data) return null;

  const metrics = [
    {
      icon: Upload,
      label: 'Studies Uploaded',
      value: data.upload_count.toString(),
      color: 'text-medical-600 dark:text-medical-400',
      bg: 'bg-medical-50 dark:bg-medical-900/20',
    },
    {
      icon: Brain,
      label: 'Analyses Run',
      value: data.analysis_count.toString(),
      sub: data.analysis_count > 0
        ? `${data.completed_analyses} completed`
        : undefined,
      color: 'text-purple-600 dark:text-purple-400',
      bg: 'bg-purple-50 dark:bg-purple-900/20',
    },
    {
      icon: HardDrive,
      label: 'Storage Used',
      value: formatFileSize(data.total_storage_bytes),
      color: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-900/20',
    },
    {
      icon: Clock,
      label: 'Last Active',
      value: data.last_active_at
        ? new Date(data.last_active_at).toLocaleDateString()
        : 'N/A',
      color: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    },
  ];

  return (
    <div className="medical-card p-6">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
        My Activity
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.label} className={`${metric.bg} rounded-lg p-4`}>
              <Icon className={`w-5 h-5 ${metric.color} mb-2`} />
              <div className="text-xl font-bold text-slate-900 dark:text-white">
                {metric.value}
              </div>
              <div className="text-xs text-slate-600 dark:text-slate-400">
                {metric.label}
              </div>
              {metric.sub && (
                <div className="text-xs text-slate-500 dark:text-slate-500 mt-1">
                  {metric.sub}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MyActivityCard;
