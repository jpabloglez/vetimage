/**
 * Study Table View
 *
 * Sortable table with inline thumbnails for study browsing.
 */

import React, { useState } from 'react';
import { ArrowUpDown, Eye, Trash2 } from 'lucide-react';
import { formatDicomDateDisplay, type Study } from '../../utils/api';

interface StudyTableViewProps {
  studies: Study[];
  onStudySelect: (studyUID: string) => void;
  onStudyDelete: (studyUID: string) => void;
}

type SortKey = 'PatientName' | 'PatientID' | 'StudyDate' | 'Modality' | 'NumberOfStudyRelatedSeries';

export const StudyTableView: React.FC<StudyTableViewProps> = ({
  studies,
  onStudySelect,
  onStudyDelete,
}) => {
  const [sortKey, setSortKey] = useState<SortKey>('StudyDate');
  const [sortAsc, setSortAsc] = useState(false);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const sorted = [...studies].sort((a, b) => {
    const aVal = a[sortKey] ?? '';
    const bVal = b[sortKey] ?? '';
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortAsc ? aVal - bVal : bVal - aVal;
    }
    const aStr = String(aVal);
    const bStr = String(bVal);
    return sortAsc ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
  });

  const SortHeader: React.FC<{ label: string; field: SortKey }> = ({ label, field }) => (
    <th
      className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300 cursor-pointer hover:text-medical-600 dark:hover:text-medical-400"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        <ArrowUpDown className="w-3 h-3" />
      </div>
    </th>
  );

  return (
    <div className="medical-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-50 dark:bg-slate-800">
            <tr>
              <SortHeader label="Patient Name" field="PatientName" />
              <SortHeader label="Patient ID" field="PatientID" />
              <SortHeader label="Study Date" field="StudyDate" />
              <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">
                Description
              </th>
              <SortHeader label="Modality" field="Modality" />
              <SortHeader label="Series" field="NumberOfStudyRelatedSeries" />
              <th className="text-left py-3 px-4 text-sm font-medium text-slate-700 dark:text-slate-300">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {sorted.map((study) => (
              <tr
                key={study.StudyInstanceUID}
                className="hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer"
                onClick={() => onStudySelect(study.StudyInstanceUID)}
              >
                <td className="py-3 px-4 text-sm font-medium text-slate-900 dark:text-white">
                  {study.PatientName || 'Unknown'}
                </td>
                <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                  {study.PatientID || 'N/A'}
                </td>
                <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                  {study.StudyDate ? formatDicomDateDisplay(study.StudyDate) : 'Unknown'}
                </td>
                <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400 max-w-xs truncate">
                  {study.StudyDescription || 'No description'}
                </td>
                <td className="py-3 px-4">
                  {study.Modality && (
                    <span className="inline-flex px-2 py-1 rounded text-xs font-medium bg-medical-100 text-medical-700 dark:bg-medical-900/30 dark:text-medical-400">
                      {study.Modality}
                    </span>
                  )}
                </td>
                <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                  {study.NumberOfStudyRelatedSeries || 0} series / {study.NumberOfStudyRelatedInstances || 0} images
                </td>
                <td className="py-3 px-4">
                  <div className="flex gap-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); onStudySelect(study.StudyInstanceUID); }}
                      className="p-1.5 hover:bg-medical-100 dark:hover:bg-medical-900 rounded transition-colors"
                      title="View study"
                    >
                      <Eye className="w-4 h-4 text-medical-600 dark:text-medical-400" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); onStudyDelete(study.StudyInstanceUID); }}
                      className="p-1.5 hover:bg-error-100 dark:hover:bg-error-900 rounded transition-colors"
                      title="Delete study"
                    >
                      <Trash2 className="w-4 h-4 text-error-600 dark:text-error-400" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default StudyTableView;
