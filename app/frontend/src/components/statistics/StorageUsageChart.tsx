/**
 * Storage Usage Chart
 *
 * LineChart showing cumulative storage usage over time.
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { formatFileSize } from '../../utils/api';

interface StorageUsageChartProps {
  title: string;
  data: Array<{ date: string; cumulative_bytes: number; period_bytes: number }>;
  height?: number;
}

export const StorageUsageChart: React.FC<StorageUsageChartProps> = ({
  title,
  data,
  height = 300,
}) => {
  if (!data || data.length === 0) return null;

  const chartData = data.map((item) => ({
    date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    storage: item.cumulative_bytes,
  }));

  return (
    <div className="medical-card p-6">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
        {title}
      </h3>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => formatFileSize(value)}
          />
          <Tooltip
            formatter={(value: number) => [formatFileSize(value), 'Total Storage']}
          />
          <Line
            type="monotone"
            dataKey="storage"
            stroke="#8b5cf6"
            strokeWidth={2}
            dot={false}
            name="Cumulative Storage"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default StorageUsageChart;
