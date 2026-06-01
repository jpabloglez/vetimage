/**
 * Study Comparison Selector
 *
 * Allows selecting two studies from the same patient for side-by-side comparison.
 */

import React, { useState, useEffect } from 'react';
import { Columns2, Search } from 'lucide-react';
import { apiClient, formatDicomDateDisplay, type Study } from '../../utils/api';
import Button from '../ui/Button';

interface StudyComparisonSelectorProps {
  currentStudyUID: string;
  patientID: string;
  onCompare: (leftUID: string, rightUID: string) => void;
}

export const StudyComparisonSelector: React.FC<StudyComparisonSelectorProps> = ({
  currentStudyUID,
  patientID,
  onCompare,
}) => {
  const [studies, setStudies] = useState<Study[]>([]);
  const [selectedUID, setSelectedUID] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadPatientStudies = async () => {
      setLoading(true);
      try {
        const allStudies = await apiClient.getStudies({ patientID });
        // Exclude current study from options
        setStudies(allStudies.filter((s) => s.StudyInstanceUID !== currentStudyUID));
      } catch {
        setStudies([]);
      } finally {
        setLoading(false);
      }
    };
    loadPatientStudies();
  }, [patientID, currentStudyUID]);

  if (loading) {
    return (
      <div className="p-4 text-sm text-slate-400">Loading patient studies...</div>
    );
  }

  if (studies.length === 0) {
    return (
      <div className="p-4 text-sm text-slate-400">
        No other studies found for this patient.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
        <Columns2 className="w-4 h-4" />
        Compare with another study
      </h4>

      <div className="space-y-2 max-h-48 overflow-y-auto">
        {studies.map((study) => (
          <button
            key={study.StudyInstanceUID}
            onClick={() => setSelectedUID(study.StudyInstanceUID)}
            className={`w-full text-left p-2 rounded-lg text-sm transition-colors ${
              selectedUID === study.StudyInstanceUID
                ? 'bg-medical-500/20 border border-medical-500'
                : 'bg-slate-700/50 border border-slate-600 hover:bg-slate-700'
            }`}
          >
            <p className="font-medium text-slate-200 truncate">
              {study.StudyDescription || 'No description'}
            </p>
            <p className="text-xs text-slate-400">
              {study.StudyDate ? formatDicomDateDisplay(study.StudyDate) : 'Unknown date'}
              {study.Modality && ` • ${study.Modality}`}
            </p>
          </button>
        ))}
      </div>

      {selectedUID && (
        <Button
          variant="medical"
          size="sm"
          fullWidth
          leftIcon={Columns2}
          onClick={() => onCompare(currentStudyUID, selectedUID)}
        >
          Compare Studies
        </Button>
      )}
    </div>
  );
};

export default StudyComparisonSelector;
