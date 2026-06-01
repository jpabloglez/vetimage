/**
 * Model Trends Chart
 *
 * LineChart showing per-model success rate trends over time.
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
  Legend,
} from 'recharts';
import type { ModelTrend } from '../../utils/api';

interface ModelTrendsChartProps {
  title: string;
  data: ModelTrend[];
  height?: number;
}

const COLORS = [
  '#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444',
  '#ec4899', '#6366f1', '#14b8a6',
];

export const ModelTrendsChart: React.FC<ModelTrendsChartProps> = ({
  title,
  data,
  height = 300,
}) => {
  if (!data || data.length === 0) return null;

  // Group by date with models as separate keys
  const dateMap = new Map<string, Record<string, number>>();
  const modelKeys = new Set<string>();

  for (const item of data) {
    modelKeys.add(item.model_name);
    if (!dateMap.has(item.date)) {
      dateMap.set(item.date, {});
    }
    dateMap.get(item.date)![item.model_name] = item.success_rate;
  }

  const chartData = Array.from(dateMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, values]) => ({
      date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      ...values,
    }));

  const models = Array.from(modelKeys);

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
            tickFormatter={(v) => `${v}%`}
            domain={[0, 100]}
          />
          <Tooltip formatter={(value: number) => [`${value}%`, 'Success Rate']} />
          <Legend />
          {models.map((model, idx) => (
            <Line
              key={model}
              type="monotone"
              dataKey={model}
              stroke={COLORS[idx % COLORS.length]}
              strokeWidth={2}
              dot={false}
              name={model}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ModelTrendsChart;
