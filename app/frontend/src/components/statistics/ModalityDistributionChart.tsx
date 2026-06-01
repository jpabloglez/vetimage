/**
 * Modality Distribution Chart
 *
 * PieChart showing distribution of imaging modalities (CT, MR, etc.)
 */

import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface ModalityDistributionChartProps {
  title: string;
  data: Array<{ modality: string; count: number }>;
  height?: number;
}

const COLORS = [
  '#0ea5e9', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444',
  '#ec4899', '#6366f1', '#14b8a6', '#f97316', '#06b6d4',
];

export const ModalityDistributionChart: React.FC<ModalityDistributionChartProps> = ({
  title,
  data,
  height = 300,
}) => {
  if (!data || data.length === 0) return null;

  const chartData = data.map((item) => ({
    name: item.modality || 'Unknown',
    value: item.count,
  }));

  return (
    <div className="medical-card p-6">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
        {title}
      </h3>
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) =>
              `${name} (${(percent * 100).toFixed(0)}%)`
            }
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((_entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ModalityDistributionChart;
