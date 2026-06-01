/**
 * Model Usage Chart Component
 *
 * Displays AI model usage statistics using a bar chart.
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
} from 'recharts';

interface ModelUsageData {
  model_name: string;
  model_key: string;
  count: number;
}

interface ModelUsageChartProps {
  title: string;
  data: ModelUsageData[];
  height?: number;
}

export const ModelUsageChart: React.FC<ModelUsageChartProps> = ({
  title,
  data,
  height = 300,
}) => {
  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) {
      return null;
    }

    const data = payload[0].payload;

    return (
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-3 shadow-lg">
        <p className="text-sm font-medium text-slate-900 dark:text-white mb-1">
          {data.model_name}
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">
          {data.model_key}
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Tasks: <span className="font-semibold text-medical-500">{data.count}</span>
        </p>
      </div>
    );
  };

  // Handle empty data
  if (!data || data.length === 0) {
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
        <BarChart
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            className="stroke-slate-200 dark:stroke-slate-700"
          />
          <XAxis
            dataKey="model_name"
            className="text-xs text-slate-600 dark:text-slate-400"
            stroke="currentColor"
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis
            className="text-xs text-slate-600 dark:text-slate-400"
            stroke="currentColor"
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            formatter={() => (
              <span className="text-sm text-slate-700 dark:text-slate-300">
                Task Count
              </span>
            )}
          />
          <Bar
            dataKey="count"
            fill="#0ea5e9"
            radius={[8, 8, 0, 0]}
            name="Task Count"
          />
        </BarChart>
      </ResponsiveContainer>

      {/* Summary */}
      <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
        <div className="grid grid-cols-2 gap-4 text-center">
          <div>
            <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">
              Total Models
            </div>
            <div className="text-lg font-semibold text-slate-900 dark:text-white">
              {data.length}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">
              Most Used
            </div>
            <div className="text-lg font-semibold text-slate-900 dark:text-white truncate">
              {data.reduce((max, item) => (item.count > max.count ? item : max), data[0])
                ?.model_name || 'N/A'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModelUsageChart;
