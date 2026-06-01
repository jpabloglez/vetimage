/**
 * Study Browser Component
 *
 * Displays list of uploaded DICOM studies with:
 * - Grid and table view modes
 * - Study metadata cards
 * - Search and filter functionality
 * - Click to open in OHIF Viewer
 * - Study management (delete, view details)
 */

import React, { useState, useEffect } from 'react';
import { Search, Eye, Trash2, Calendar, User, Activity, Folder } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient, formatDicomDateDisplay, type Study } from '../../utils/api';
import Button from '../ui/Button';
import Input from '../ui/Input';
import { StudyTableView } from '../studies/StudyTableView';
import { ViewToggle, type ViewMode } from '../studies/ViewToggle';

interface StudyBrowserProps {
  onStudySelect?: (studyUID: string) => void;
  refreshTrigger?: number;
}

export const StudyBrowser: React.FC<StudyBrowserProps> = ({ onStudySelect, refreshTrigger }) => {
  const [studies, setStudies] = useState<Study[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredStudies, setFilteredStudies] = useState<Study[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');

  // Load studies
  const loadStudies = async () => {
    setLoading(true);
    try {
      const data = await apiClient.getStudies();
      setStudies(data);
      setFilteredStudies(data);
    } catch (error: any) {
      console.error('Failed to load studies:', error);
      toast.error(error.error || 'Failed to load studies');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStudies();
  }, [refreshTrigger]);

  // Filter studies based on search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredStudies(studies);
      return;
    }

    const query = searchQuery.toLowerCase();
    const filtered = studies.filter(study =>
      study.PatientID?.toLowerCase().includes(query) ||
      study.PatientName?.toLowerCase().includes(query) ||
      study.StudyDescription?.toLowerCase().includes(query)
    );
    setFilteredStudies(filtered);
  }, [searchQuery, studies]);

  const handleViewStudy = (studyUID: string) => {
    if (onStudySelect) {
      onStudySelect(studyUID);
    }
  };

  const handleDeleteStudy = async (studyUID: string) => {
    if (!confirm('Are you sure you want to delete this study? This action cannot be undone.')) {
      return;
    }

    try {
      await apiClient.deleteStudy(studyUID);
      toast.success('Study deleted successfully');
      loadStudies();
    } catch (error: any) {
      console.error('Failed to delete study:', error);
      toast.error(error.error || 'Failed to delete study');
    }
  };

  if (loading) {
    return (
      <div className="medical-card p-12 text-center">
        <div className="w-12 h-12 border-4 border-medical-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-600 dark:text-slate-400">Loading studies...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Search Bar */}
      <div className="medical-card p-4">
        <Input
          type="text"
          placeholder="Search by Patient ID, Name, or Study Description..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          leftIcon={Search}
        />
      </div>

      {/* Studies Count + View Toggle */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          Studies ({filteredStudies.length})
        </h3>
        <div className="flex items-center gap-3">
          <ViewToggle viewMode={viewMode} onViewChange={setViewMode} />
          <Button
            variant="ghost"
            size="sm"
            onClick={loadStudies}
            disabled={loading}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Empty State */}
      {filteredStudies.length === 0 ? (
        <div className="medical-card p-12 text-center">
          <Folder className="w-16 h-16 mx-auto mb-4 text-slate-300 dark:text-slate-600" />
          <h3 className="text-xl font-semibold mb-2 text-slate-900 dark:text-slate-100">
            {searchQuery ? 'No studies found' : 'No studies yet'}
          </h3>
          <p className="text-slate-600 dark:text-slate-400">
            {searchQuery
              ? 'Try adjusting your search query'
              : 'Upload DICOM files to get started'
            }
          </p>
        </div>
      ) : viewMode === 'table' ? (
        /* Table View */
        <StudyTableView
          studies={filteredStudies}
          onStudySelect={handleViewStudy}
          onStudyDelete={handleDeleteStudy}
        />
      ) : (
        /* Grid View */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredStudies.map((study) => (
            <div
              key={study.StudyInstanceUID}
              className="medical-card p-6 hover:shadow-lg transition-shadow cursor-pointer group"
              onClick={() => handleViewStudy(study.StudyInstanceUID)}
            >
              {/* Study Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1 min-w-0">
                  <h4 className="text-lg font-semibold text-slate-900 dark:text-slate-100 truncate mb-1">
                    {study.PatientName || 'Unknown Patient'}
                  </h4>
                  <p className="text-sm text-slate-600 dark:text-slate-400 truncate">
                    {study.StudyDescription || 'No description'}
                  </p>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleViewStudy(study.StudyInstanceUID);
                    }}
                    className="p-2 hover:bg-medical-100 dark:hover:bg-medical-900 rounded transition-colors"
                    title="View in OHIF Viewer"
                  >
                    <Eye className="w-4 h-4 text-medical-600 dark:text-medical-400" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteStudy(study.StudyInstanceUID);
                    }}
                    className="p-2 hover:bg-error-100 dark:hover:bg-error-900 rounded transition-colors"
                    title="Delete study"
                  >
                    <Trash2 className="w-4 h-4 text-error-600 dark:text-error-400" />
                  </button>
                </div>
              </div>

              {/* Study Metadata */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                  <User className="w-4 h-4" />
                  <span>ID: {study.PatientID || 'Unknown'}</span>
                </div>

                <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                  <Calendar className="w-4 h-4" />
                  <span>{study.StudyDate ? formatDicomDateDisplay(study.StudyDate) : 'Unknown date'}</span>
                </div>

                <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                  <Activity className="w-4 h-4" />
                  <span>
                    {study.NumberOfStudyRelatedSeries || 0} series •{' '}
                    {study.NumberOfStudyRelatedInstances || 0} images
                  </span>
                </div>
              </div>

              {/* View Button (Mobile) */}
              <div className="mt-4 sm:hidden">
                <Button
                  variant="medical"
                  size="sm"
                  fullWidth
                  leftIcon={Eye}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleViewStudy(study.StudyInstanceUID);
                  }}
                >
                  View Study
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default StudyBrowser;
