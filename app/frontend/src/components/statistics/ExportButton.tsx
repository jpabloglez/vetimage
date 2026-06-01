/**
 * Export Button Component
 *
 * Provides export functionality for statistics data in CSV and JSON formats.
 */

import React, { useState } from 'react';
import { Download, FileText, FileJson, ChevronDown } from 'lucide-react';
import { StatisticsTask } from '../../utils/api';

interface ExportButtonProps {
  data: StatisticsTask[];
  filename?: string;
}

export const ExportButton: React.FC<ExportButtonProps> = ({
  data,
  filename = 'statistics',
}) => {
  const [isOpen, setIsOpen] = useState(false);

  /**
   * Convert data to CSV format
   */
  const exportToCSV = () => {
    if (data.length === 0) {
      alert('No data to export');
      return;
    }

    // Define CSV headers
    const headers = [
      'Task ID',
      'Model Name',
      'Model Key',
      'Model Type',
      'Status',
      'Patient ID',
      'Patient Sex',
      'Patient Age',
      'Study Date',
      'Study Description',
      'Modality',
      'Body Part',
      'Organization',
      'Created At',
      'Completed At',
      'Processing Duration (s)',
    ];

    // Convert data to CSV rows
    const rows = data.map((task) => [
      task.id,
      task.model_name,
      task.model_key,
      task.model_type,
      task.status,
      task.patient_id || '',
      task.patient_sex || '',
      task.patient_age?.toString() || '',
      task.study_date || '',
      task.study_description || '',
      task.modality || '',
      task.body_part || '',
      task.organization_name || '',
      task.created_at,
      task.completed_at || '',
      task.processing_duration?.toString() || '',
    ]);

    // Combine headers and rows
    const csvContent = [
      headers.join(','),
      ...rows.map((row) =>
        row.map((cell) => `"${cell?.toString().replace(/"/g, '""') || ''}"`).join(',')
      ),
    ].join('\n');

    // Create blob and download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);

    setIsOpen(false);
  };

  /**
   * Export data as JSON
   */
  const exportToJSON = () => {
    if (data.length === 0) {
      alert('No data to export');
      return;
    }

    const jsonContent = JSON.stringify(
      {
        exported_at: new Date().toISOString(),
        total_records: data.length,
        data: data,
      },
      null,
      2
    );

    const blob = new Blob([jsonContent], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);

    setIsOpen(false);
  };

  return (
    <div className="relative">
      {/* Main Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={data.length === 0}
        className={`
          flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors
          ${
            data.length === 0
              ? 'bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed'
              : 'bg-medical-500 hover:bg-medical-600 text-white'
          }
        `}
      >
        <Download className="w-4 h-4" />
        Export
        <ChevronDown className="w-4 h-4" />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Menu */}
          <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg z-20">
            <button
              onClick={exportToCSV}
              className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors rounded-t-lg"
            >
              <FileText className="w-4 h-4 text-slate-600 dark:text-slate-400" />
              <div className="text-left">
                <div className="text-sm font-medium text-slate-900 dark:text-white">
                  Export as CSV
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  Comma-separated values
                </div>
              </div>
            </button>

            <button
              onClick={exportToJSON}
              className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors rounded-b-lg"
            >
              <FileJson className="w-4 h-4 text-slate-600 dark:text-slate-400" />
              <div className="text-left">
                <div className="text-sm font-medium text-slate-900 dark:text-white">
                  Export as JSON
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  JavaScript Object Notation
                </div>
              </div>
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ExportButton;
