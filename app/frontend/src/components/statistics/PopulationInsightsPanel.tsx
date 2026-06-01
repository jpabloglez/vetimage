/**
 * Population Insights Panel
 *
 * Age histogram, gender distribution pie, and top findings list.
 */

import React from 'react';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { PopulationInsights } from '../../utils/api';

interface PopulationInsightsPanelProps {
  data: PopulationInsights | null;
}

const GENDER_COLORS: Record<string, string> = {
  M: '#0ea5e9',
  F: '#ec4899',
  O: '#8b5cf6',
};

const GENDER_LABELS: Record<string, string> = {
  M: 'Male',
  F: 'Female',
  O: 'Other',
};

export const PopulationInsightsPanel: React.FC<PopulationInsightsPanelProps> = ({ data }) => {
  if (!data) return null;

  const genderData = data.gender_distribution.map((g) => ({
    name: GENDER_LABELS[g.patient_sex] || g.patient_sex,
    value: g.count,
    color: GENDER_COLORS[g.patient_sex] || '#6b7280',
  }));

  return (
    <div className="space-y-6">
      <div className="medical-card p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">
          Population Insights
        </h3>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
          {data.total_patients} unique patients
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Age Histogram */}
          <div>
            <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
              Age Distribution
            </h4>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.age_histogram}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis dataKey="bracket" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#0ea5e9" name="Patients" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Gender Distribution */}
          <div>
            <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
              Gender Distribution
            </h4>
            {genderData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={genderData}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, percent }) =>
                      `${name} (${(percent * 100).toFixed(0)}%)`
                    }
                    dataKey="value"
                  >
                    {genderData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-slate-500 dark:text-slate-400">No gender data available</p>
            )}
          </div>
        </div>
      </div>

      {/* Top Findings */}
      {data.top_findings.length > 0 && (
        <div className="medical-card p-6">
          <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
            Top AI Findings
          </h4>
          <div className="space-y-2">
            {data.top_findings.slice(0, 10).map((finding, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between py-2 px-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
              >
                <span className="text-sm text-slate-700 dark:text-slate-300 truncate flex-1">
                  {finding.finding}
                </span>
                <span className="text-sm font-medium text-medical-600 dark:text-medical-400 ml-3">
                  {finding.count}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PopulationInsightsPanel;
