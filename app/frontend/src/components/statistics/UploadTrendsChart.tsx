/**
 * Upload Trends Chart
 *
 * AreaChart showing study upload volume over time with period selector.
 */

import React, { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface UploadTrendsChartProps {
  title: string;
  data: Array<{ date: string; count: number }>;
  height?: number;
  onPeriodChange?: (period: string) => void;
}

export const UploadTrendsChart: React.FC<UploadTrendsChartProps> = ({
  title,
  data,
  height = 300,
  onPeriodChange,
}) => {
  const [period, setPeriod] = useState('daily');

  const handlePeriodChange = (newPeriod: string) => {
    setPeriod(newPeriod);
    onPeriodChange?.(newPeriod);
  };

  if (!data || data.length === 0) return null;

  const chartData = data.map((item) => ({
    date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    uploads: item.count,
  }));

  return (
    <div className="medical-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
          {title}
        </h3>
        <div className="flex gap-1">
          {['daily', 'weekly', 'monthly'].map((p) => (
            <button
              key={p}
              onClick={() => handlePeriodChange(p)}
              className={`px-3 py-1 text-xs rounded-lg font-medium transition-colors ${
                period === p
                  ? 'bg-medical-500 text-white'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'
              }`}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Area
            type="monotone"
            dataKey="uploads"
            stroke="#0ea5e9"
            fill="#0ea5e9"
            fillOpacity={0.2}
            name="Uploads"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default UploadTrendsChart;
