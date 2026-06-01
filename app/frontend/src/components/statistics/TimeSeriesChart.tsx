/**
 * Time Series Chart Component
 *
 * Displays time-based data using Recharts line chart.
 * Used for visualizing trends over time (e.g., tasks per day, processing times).
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

interface TimeSeriesDataPoint {
  date: string;
  value: number;
  label?: string;
}

interface TimeSeriesChartProps {
  /**
   * Chart title displayed above the visualization
   */
  title: string;

  /**
   * Array of data points with date and value
   */
  data: TimeSeriesDataPoint[];

  /**
   * Label for the data series (shown in legend)
   */
  dataLabel?: string;

  /**
   * Color of the line (hex, rgb, or named color)
   */
  lineColor?: string;

  /**
   * Y-axis label
   */
  yAxisLabel?: string;

  /**
   * Chart height in pixels
   */
  height?: number;

  /**
   * Show grid lines
   */
  showGrid?: boolean;

  /**
   * Show legend
   */
  showLegend?: boolean;
}

export const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  title,
  data,
  dataLabel = 'Value',
  lineColor = '#0ea5e9',
  yAxisLabel,
  height = 300,
  showGrid = true,
  showLegend = false,
}) => {
  /**
   * Format date for display (shorter format for X-axis)
   */
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      // Format as MM/DD if valid date
      if (!isNaN(date.getTime())) {
        return `${date.getMonth() + 1}/${date.getDate()}`;
      }
      return dateString;
    } catch {
      return dateString;
    }
  };

  /**
   * Custom tooltip content
   */
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) {
      return null;
    }

    const data = payload[0].payload;

    return (
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-3 shadow-lg">
        <p className="text-sm font-medium text-slate-900 dark:text-white mb-1">
          {new Date(data.date).toLocaleDateString()}
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          {dataLabel}: <span className="font-semibold text-medical-500">{data.value}</span>
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
        <LineChart
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              className="stroke-slate-200 dark:stroke-slate-700"
            />
          )}

          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            className="text-xs text-slate-600 dark:text-slate-400"
            stroke="currentColor"
          />

          <YAxis
            label={
              yAxisLabel
                ? {
                    value: yAxisLabel,
                    angle: -90,
                    position: 'insideLeft',
                    className: 'text-xs text-slate-600 dark:text-slate-400',
                  }
                : undefined
            }
            className="text-xs text-slate-600 dark:text-slate-400"
            stroke="currentColor"
          />

          <Tooltip content={<CustomTooltip />} />

          {showLegend && (
            <Legend
              wrapperStyle={{
                paddingTop: '20px',
              }}
            />
          )}

          <Line
            type="monotone"
            dataKey="value"
            name={dataLabel}
            stroke={lineColor}
            strokeWidth={2}
            dot={{
              fill: lineColor,
              r: 4,
            }}
            activeDot={{
              r: 6,
              stroke: lineColor,
              strokeWidth: 2,
              fill: '#fff',
            }}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Data Summary */}
      <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">
              Data Points
            </div>
            <div className="text-sm font-semibold text-slate-900 dark:text-white">
              {data.length}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">
              Maximum
            </div>
            <div className="text-sm font-semibold text-slate-900 dark:text-white">
              {Math.max(...data.map(d => d.value))}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">
              Average
            </div>
            <div className="text-sm font-semibold text-slate-900 dark:text-white">
              {(data.reduce((sum, d) => sum + d.value, 0) / data.length).toFixed(1)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimeSeriesChart;
