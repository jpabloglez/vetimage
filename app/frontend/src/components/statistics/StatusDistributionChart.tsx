/**
 * Status Distribution Chart Component
 *
 * Displays task status breakdown using a pie chart.
 */

import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface StatusDistributionChartProps {
  title: string;
  data: Record<string, number>;
  height?: number;
}

const STATUS_COLORS: Record<string, string> = {
  COMPLETED: '#10b981', // green
  FAILED: '#ef4444', // red
  PROCESSING: '#f59e0b', // amber
  QUEUED: '#3b82f6', // blue
  PENDING: '#6b7280', // gray
  DISPATCHED: '#8b5cf6', // purple
  CANCELLED: '#6b7280', // gray
  TIMEOUT: '#dc2626', // red-600
};

export const StatusDistributionChart: React.FC<StatusDistributionChartProps> = ({
  title,
  data,
  height = 300,
}) => {
  // Convert data object to array format for Recharts
  const chartData = Object.entries(data).map(([status, count]) => ({
    name: status,
    value: count,
    color: STATUS_COLORS[status] || '#6b7280',
  }));

  // Calculate totals
  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) {
      return null;
    }

    const data = payload[0];
    const percentage = total > 0 ? ((data.value / total) * 100).toFixed(1) : 0;

    return (
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-3 shadow-lg">
        <p className="text-sm font-medium text-slate-900 dark:text-white mb-1">
          {data.name}
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Count: <span className="font-semibold">{data.value}</span>
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Percentage: <span className="font-semibold">{percentage}%</span>
        </p>
      </div>
    );
  };

  // Custom label
  const renderCustomLabel = ({ name, percent }: any) => {
    const percentage = (percent * 100).toFixed(0);
    return percentage > 5 ? `${percentage}%` : '';
  };

  // Handle empty data
  if (chartData.length === 0 || total === 0) {
    return (
      <div className="medical-card p-6">
        <h3 className="text-lg font-semibold mb-4 text-slate-900 dark:text-white">
          {title}
        </h3>
        <div className="flex items-center justify-center h-64 text-slate-500 dark:text-slate-400">
          No data available
        </div>
      </div>
    );
  }

  return (
    <div className="medical-card p-6">
      <h3 className="text-lg font-semibold mb-4 text-slate-900 dark:text-white">
        {title}
      </h3>

      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomLabel}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="bottom"
            height={36}
            formatter={(value) => (
              <span className="text-sm text-slate-700 dark:text-slate-300">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* Summary */}
      <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
        <div className="text-center">
          <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">
            Total Tasks
          </div>
          <div className="text-2xl font-semibold text-slate-900 dark:text-white">
            {total}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatusDistributionChart;
