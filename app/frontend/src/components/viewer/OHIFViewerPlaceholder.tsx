/**
 * OHIF Viewer Placeholder Component
 *
 * Minimal viewer component for the vertical slice implementation.
 * This demonstrates the structure and will be replaced with full
 * OHIF Viewer integration in future iterations.
 *
 * For now, it displays study information and provides a foundation
 * for the complete OHIF implementation.
 */

import React, { useState, useEffect } from 'react';
import { Eye, Layers, Image as ImageIcon, Info, ArrowLeft } from 'lucide-react';
import { apiClient, formatDicomDateDisplay, type Study, type Series } from '../../utils/api';
import Button from '../ui/Button';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import toast from 'react-hot-toast';

interface OHIFViewerPlaceholderProps {
  studyUID: string;
  onClose?: () => void;
}

export const OHIFViewerPlaceholder: React.FC<OHIFViewerPlaceholderProps> = ({
  studyUID,
  onClose,
}) => {
  const [loading, setLoading] = useState(true);
  const [study, setStudy] = useState<Study | null>(null);
  const [series, setSeries] = useState<Series[]>([]);

  useEffect(() => {
    loadStudyData();
  }, [studyUID]);

  const loadStudyData = async () => {
    setLoading(true);
    try {
      // Get study metadata
      const studies = await apiClient.getStudies({ limit: 1000 });
      const foundStudy = studies.find(s => s.StudyInstanceUID === studyUID);

      if (!foundStudy) {
        toast.error('Study not found');
        return;
      }

      setStudy(foundStudy);

      // Get series for this study
      const seriesData = await apiClient.getSeries(studyUID);
      setSeries(seriesData);

    } catch (error: any) {
      console.error('Failed to load study:', error);
      toast.error(error.error || 'Failed to load study data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 pt-20 px-4">
        <div className="container mx-auto">
          <div className="medical-card p-12 text-center">
            <div className="w-16 h-16 border-4 border-medical-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-lg text-slate-600 dark:text-slate-400">Loading study...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!study) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 pt-20 px-4">
        <div className="container mx-auto">
          <div className="medical-card p-12 text-center">
            <Info className="w-16 h-16 mx-auto mb-4 text-slate-300 dark:text-slate-600" />
            <h2 className="text-2xl font-bold mb-2 text-slate-900 dark:text-slate-100">Study not found</h2>
            <p className="text-slate-600 dark:text-slate-400 mb-6">
              The requested study could not be loaded.
            </p>
            {onClose && (
              <Button variant="medical" onClick={onClose} leftIcon={ArrowLeft}>
                Back to Studies
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 pt-20">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            {onClose && (
              <Button variant="ghost" size="sm" onClick={onClose} leftIcon={ArrowLeft}>
                Back
              </Button>
            )}
            <div>
              <h1 className="text-3xl font-bold medical-gradient-text">DICOM Viewer</h1>
              <p className="text-slate-600 dark:text-slate-400">Study: {study.PatientName || 'Unknown'}</p>
            </div>
          </div>
        </div>

        {/* OHIF Viewer Placeholder */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Viewer Area */}
          <div className="lg:col-span-2">
            <Card variant="medical">
              <CardHeader>
                <CardTitle>
                  <div className="flex items-center gap-2">
                    <Eye className="w-5 h-5" />
                    OHIF Viewer (Coming Soon)
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-slate-900 rounded-lg p-12 text-center min-h-[500px] flex items-center justify-center">
                  <div>
                    <Eye className="w-24 h-24 mx-auto mb-6 text-slate-600" />
                    <h3 className="text-2xl font-bold mb-4 text-slate-300">OHIF Viewer Integration</h3>
                    <p className="text-slate-400 mb-6 max-w-md mx-auto">
                      The OHIF Viewer will be fully integrated here to provide advanced
                      DICOM image viewing, manipulation, and analysis capabilities.
                    </p>
                    <div className="space-y-2 text-sm text-slate-500 text-left max-w-md mx-auto">
                      <p>✓ DICOM data successfully uploaded and stored</p>
                      <p>✓ DICOMweb API endpoints configured</p>
                      <p>✓ Study metadata available for viewing</p>
                      <p>✓ Ready for OHIF Viewer integration</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Study Information Sidebar */}
          <div className="space-y-6">
            {/* Study Details */}
            <Card>
              <CardHeader>
                <CardTitle>Study Information</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-3">
                  <div>
                    <dt className="text-sm font-medium text-slate-600 dark:text-slate-400">Patient Name</dt>
                    <dd className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {study.PatientName || 'Unknown'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-slate-600 dark:text-slate-400">Patient ID</dt>
                    <dd className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {study.PatientID || 'Unknown'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-slate-600 dark:text-slate-400">Study Date</dt>
                    <dd className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {study.StudyDate ? formatDicomDateDisplay(study.StudyDate) : 'Unknown'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-slate-600 dark:text-slate-400">Description</dt>
                    <dd className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {study.StudyDescription || 'No description'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-slate-600 dark:text-slate-400">Accession Number</dt>
                    <dd className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {study.AccessionNumber || 'N/A'}
                    </dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

            {/* Series List */}
            <Card>
              <CardHeader>
                <CardTitle>
                  <div className="flex items-center gap-2">
                    <Layers className="w-5 h-5" />
                    Series ({series.length})
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {series.length === 0 ? (
                  <p className="text-sm text-slate-600 dark:text-slate-400 text-center py-4">
                    No series found
                  </p>
                ) : (
                  <div className="space-y-3">
                    {series.map((s, index) => (
                      <div
                        key={s.SeriesInstanceUID}
                        className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                            Series {s.SeriesNumber || index + 1}
                          </span>
                          <span className="text-xs px-2 py-1 bg-medical-100 dark:bg-medical-900 text-medical-700 dark:text-medical-300 rounded">
                            {s.Modality}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">
                          {s.SeriesDescription || 'No description'}
                        </p>
                        <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                          <ImageIcon className="w-3 h-3" />
                          <span>{s.NumberOfSeriesRelatedInstances || 0} images</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OHIFViewerPlaceholder;
