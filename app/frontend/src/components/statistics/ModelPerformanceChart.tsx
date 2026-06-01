/**
 * Model Performance Chart
 *
 * BarChart with per-model task counts and failure rate overlay.
 */

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Line,
  ComposedChart,
} from 'recharts';
import type { ModelMetric } from '../../utils/api';

interface ModelPerformanceChartProps {
  title: string;
  data: ModelMetric[];
  height?: number;
}

export const ModelPerformanceChart: React.FC<ModelPerformanceChartProps> = ({
  title,
  data,
  height = 300,
}) => {
  if (!data || data.length === 0) return null;

  const chartData = data.map((m) => ({
    name: m.model__name || m.model__key,
    completed: m.completed,
    failed: m.failed,
    timeout: m.timeout,
    failure_rate: m.failure_rate,
    avg_time: m.avg_processing_time,
  }));

  return (
    <div className="medical-card p-6">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
        {title}
      </h3>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fontSize: 12 }}
            tickFormatter={(v) => `${v}%`}
            domain={[0, 100]}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              if (name === 'failure_rate') return [`${value}%`, 'Failure Rate'];
              if (name === 'avg_time') return [value ? `${value}s` : 'N/A', 'Avg Time'];
              return [value, name.charAt(0).toUpperCase() + name.slice(1)];
            }}
          />
          <Legend />
          <Bar yAxisId="left" dataKey="completed" fill="#10b981" name="Completed" stackId="tasks" />
          <Bar yAxisId="left" dataKey="failed" fill="#ef4444" name="Failed" stackId="tasks" />
          <Bar yAxisId="left" dataKey="timeout" fill="#f59e0b" name="Timeout" stackId="tasks" />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="failure_rate"
            stroke="#ef4444"
            strokeWidth={2}
            dot={{ r: 4 }}
            name="Failure Rate"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ModelPerformanceChart;
