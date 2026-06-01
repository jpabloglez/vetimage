/**
 * OHIF Viewer Component
 *
 * Integrated DICOM viewer using Cornerstone.js for image rendering
 * This component provides medical image viewing with interactive tools,
 * window/level adjustment, and multi-series support.
 */

import React, { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Loader2 } from 'lucide-react';
import Button from '../ui/Button';
import { AIToolbarButton } from './AIToolbarButton';
import { apiClient, type Study, type Series, type Instance } from '../../utils/api';
import toast from 'react-hot-toast';
import {
  initializeCornerstone,
  enableElement,
  disableElement,
  generateImageId,
  loadAndDisplayImage,
  addBasicTools,
  resetViewport,
  fitToWindow,
} from '../../utils/cornerstoneInit';

interface OHIFViewerProps {
  studyInstanceUIDs: string[];
  onClose?: () => void;
}

/**
 * OHIF Viewer Component with Cornerstone.js Integration
 */
export const OHIFViewer: React.FC<OHIFViewerProps> = ({ studyInstanceUIDs, onClose }) => {
  const viewerContainerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [study, setStudy] = useState<Study | null>(null);
  const [series, setSeries] = useState<Series[]>([]);
  const [currentSeriesIndex, setCurrentSeriesIndex] = useState(0);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [instances, setInstances] = useState<Instance[]>([]);
  const [viewportInitialized, setViewportInitialized] = useState(false);
  const [imageLoading, setImageLoading] = useState(false);

  // Initialize Cornerstone on component mount
  useEffect(() => {
    console.log('Initializing Cornerstone libraries...');
    try {
      initializeCornerstone();
    } catch (err) {
      console.error('Failed to initialize Cornerstone:', err);
    }

    // Cleanup on unmount
    return () => {
      if (viewerContainerRef.current && viewportInitialized) {
        try {
          disableElement(viewerContainerRef.current);
        } catch (err) {
          console.warn('Error disabling viewport:', err);
        }
      }
    };
  }, []);

  // Load study data when component mounts or study UIDs change
  useEffect(() => {
    loadStudyData();
  }, [studyInstanceUIDs]);

  // Enable viewport when container ref is available
  useEffect(() => {
    if (viewerContainerRef.current && !viewportInitialized && !loading) {
      try {
        console.log('Enabling viewport...');
        enableElement(viewerContainerRef.current);
        addBasicTools(viewerContainerRef.current);
        setViewportInitialized(true);
        console.log('Viewport enabled successfully');
      } catch (err) {
        console.error('Failed to enable viewport:', err);
        toast.error('Failed to initialize viewer');
      }
    }
  }, [viewerContainerRef.current, loading, viewportInitialized]);

  // Display first image when viewport becomes ready and we have instances
  useEffect(() => {
    if (viewportInitialized && instances.length > 0 && study) {
      const currentSeries = series[currentSeriesIndex];
      if (currentSeries && instances[0]) {
        console.log('Viewport ready - displaying first image of series');
        displayImage(
          study.StudyInstanceUID,
          currentSeries.SeriesInstanceUID,
          instances[0].SOPInstanceUID,
          0
        );
      }
    }
  }, [viewportInitialized, instances, currentSeriesIndex]);

  const loadStudyData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Get study metadata
      const studies = await apiClient.getStudies({ limit: 1000 });
      const foundStudy = studies.find(s => studyInstanceUIDs.includes(s.StudyInstanceUID));

      if (!foundStudy) {
        throw new Error('Study not found');
      }

      setStudy(foundStudy);

      // Get series for this study
      const seriesData = await apiClient.getSeries(foundStudy.StudyInstanceUID);

      if (seriesData.length === 0) {
        throw new Error('No series found in study');
      }

      setSeries(seriesData);

      // Load first series
      await loadSeriesInstances(foundStudy.StudyInstanceUID, seriesData[0].SeriesInstanceUID, 0);

    } catch (err: any) {
      console.error('Failed to load study:', err);
      setError(err.message || 'Failed to load study');
      toast.error(err.message || 'Failed to load study');
    } finally {
      setLoading(false);
    }
  };

  const loadSeriesInstances = async (studyUID: string, seriesUID: string, seriesIndex: number) => {
    try {
      console.log(`Loading instances for series ${seriesIndex + 1}...`);

      // Get instances for this series
      const instancesData = await apiClient.getInstances(studyUID, seriesUID);

      if (instancesData.length === 0) {
        throw new Error('No instances found in series');
      }

      setInstances(instancesData);
      setCurrentSeriesIndex(seriesIndex);
      setCurrentImageIndex(0);

      // Note: Image will be displayed by the useEffect when viewport is ready

    } catch (err: any) {
      console.error('Failed to load series instances:', err);
      toast.error('Failed to load images for series');
    }
  };

  const displayImage = async (studyUID: string, seriesUID: string, sopUID: string, imageIndex: number) => {
    if (!viewerContainerRef.current || !viewportInitialized) {
      console.warn('Viewport not ready for image display');
      return;
    }

    setImageLoading(true);

    try {
      // Generate Cornerstone image ID
      const imageId = generateImageId(studyUID, seriesUID, sopUID, 1);

      console.log(`Displaying image ${imageIndex + 1}:`, imageId);

      // Load and display image
      await loadAndDisplayImage(viewerContainerRef.current, imageId);

      setCurrentImageIndex(imageIndex);

      console.log('Image displayed successfully');
    } catch (err: any) {
      console.error('Failed to display image:', err);
      toast.error('Failed to load image: ' + (err.message || 'Unknown error'));
    } finally {
      setImageLoading(false);
    }
  };

  const handlePreviousSeries = async () => {
    if (currentSeriesIndex > 0 && study) {
      const newIndex = currentSeriesIndex - 1;
      await loadSeriesInstances(
        study.StudyInstanceUID,
        series[newIndex].SeriesInstanceUID,
        newIndex
      );
    }
  };

  const handleNextSeries = async () => {
    if (currentSeriesIndex < series.length - 1 && study) {
      const newIndex = currentSeriesIndex + 1;
      await loadSeriesInstances(
        study.StudyInstanceUID,
        series[newIndex].SeriesInstanceUID,
        newIndex
      );
    }
  };

  const handlePreviousImage = async () => {
    if (currentImageIndex > 0 && study && instances.length > 0) {
      const newIndex = currentImageIndex - 1;
      const currentSeries = series[currentSeriesIndex];
      await displayImage(
        study.StudyInstanceUID,
        currentSeries.SeriesInstanceUID,
        instances[newIndex].SOPInstanceUID,
        newIndex
      );
    }
  };

  const handleNextImage = async () => {
    const currentSeries = series[currentSeriesIndex];
    if (currentImageIndex < instances.length - 1 && study) {
      const newIndex = currentImageIndex + 1;
      await displayImage(
        study.StudyInstanceUID,
        currentSeries.SeriesInstanceUID,
        instances[newIndex].SOPInstanceUID,
        newIndex
      );
    }
  };

  const handleSeriesClick = async (seriesIndex: number) => {
    if (study && seriesIndex !== currentSeriesIndex) {
      await loadSeriesInstances(
        study.StudyInstanceUID,
        series[seriesIndex].SeriesInstanceUID,
        seriesIndex
      );
    }
  };

  const handleResetViewport = () => {
    if (viewerContainerRef.current && viewportInitialized) {
      resetViewport(viewerContainerRef.current);
    }
  };

  const handleFitToWindow = () => {
    if (viewerContainerRef.current && viewportInitialized) {
      fitToWindow(viewerContainerRef.current);
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (loading || error) return;

      switch (event.key.toLowerCase()) {
        case 'arrowup':
          event.preventDefault();
          handlePreviousImage();
          break;
        case 'arrowdown':
          event.preventDefault();
          handleNextImage();
          break;
        case 'arrowleft':
          event.preventDefault();
          handlePreviousSeries();
          break;
        case 'arrowright':
          event.preventDefault();
          handleNextSeries();
          break;
        case ' ':
          event.preventDefault();
          handleResetViewport();
          break;
        case 'f':
          event.preventDefault();
          handleFitToWindow();
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [loading, error, currentSeriesIndex, currentImageIndex, instances]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-16 h-16 animate-spin mx-auto mb-4 text-medical-500" />
          <p className="text-lg text-slate-300">Loading viewer...</p>
          <p className="text-sm text-slate-500 mt-2">Initializing DICOM Viewer</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="max-w-md mx-auto p-8 bg-slate-800 rounded-lg text-center">
          <div className="w-16 h-16 bg-error-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl text-error-400">⚠</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100 mb-2">Error Loading Viewer</h2>
          <p className="text-slate-400 mb-6">{error}</p>
          {onClose && (
            <Button variant="medical" onClick={onClose} leftIcon={ArrowLeft}>
              Back to Studies
            </Button>
          )}
        </div>
      </div>
    );
  }

  const currentSeries = series[currentSeriesIndex];

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Viewer Header */}
      <div className="bg-slate-800 border-b border-slate-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {onClose && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                leftIcon={ArrowLeft}
                className="text-slate-300 hover:text-slate-100"
              >
                Back
              </Button>
            )}
            <div>
              <h1 className="text-lg font-semibold text-slate-100">
                {study?.PatientName || 'Unknown Patient'}
              </h1>
              <p className="text-sm text-slate-400">
                {study?.StudyDescription || 'No description'} • {study?.PatientID}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm text-slate-400">
              Series {currentSeriesIndex + 1} of {series.length} • {currentSeries?.Modality}
            </div>
            {imageLoading && (
              <Loader2 className="w-4 h-4 animate-spin text-medical-400" />
            )}
            {study && (
              <AIToolbarButton studyInstanceUID={study.StudyInstanceUID} />
            )}
          </div>
        </div>
      </div>

      {/* Main Viewer Area */}
      <div className="flex h-[calc(100vh-64px)]">
        {/* Viewer Canvas */}
        <div className="flex-1 relative bg-black">
          {/* Cornerstone Canvas */}
          <div
            ref={viewerContainerRef}
            className="w-full h-full"
            style={{
              minHeight: '500px',
            }}
          />

          {/* Tool Info Overlay */}
          <div className="absolute top-4 left-4 bg-slate-800/80 backdrop-blur-sm rounded-lg px-3 py-2 text-xs text-slate-300">
            <div>Left Click: Window/Level</div>
            <div>Middle Click: Zoom</div>
            <div>Right Click: Pan</div>
            <div>Mouse Wheel: Scroll Images</div>
            <div>Space: Reset | F: Fit</div>
          </div>

          {/* Navigation Controls Overlay */}
          <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2">
            <div className="bg-slate-800/90 backdrop-blur-sm rounded-lg p-3 flex items-center gap-2 shadow-lg border border-slate-700">
              <Button
                size="sm"
                variant="ghost"
                onClick={handlePreviousSeries}
                disabled={currentSeriesIndex === 0}
                className="text-slate-300 hover:text-slate-100 disabled:opacity-50"
              >
                ◄ Series
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handlePreviousImage}
                disabled={currentImageIndex === 0}
                className="text-slate-300 hover:text-slate-100 disabled:opacity-50"
              >
                ◄ Image
              </Button>
              <div className="px-4 text-sm text-slate-300 min-w-[100px] text-center">
                {currentImageIndex + 1} / {instances.length}
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleNextImage}
                disabled={currentImageIndex >= instances.length - 1}
                className="text-slate-300 hover:text-slate-100 disabled:opacity-50"
              >
                Image ►
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleNextSeries}
                disabled={currentSeriesIndex >= series.length - 1}
                className="text-slate-300 hover:text-slate-100 disabled:opacity-50"
              >
                Series ►
              </Button>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="absolute bottom-6 right-6 flex gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={handleResetViewport}
              className="bg-slate-800/90 backdrop-blur-sm text-slate-300 hover:text-slate-100"
            >
              Reset
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={handleFitToWindow}
              className="bg-slate-800/90 backdrop-blur-sm text-slate-300 hover:text-slate-100"
            >
              Fit
            </Button>
          </div>
        </div>

        {/* Right Sidebar - Series Thumbnails */}
        <div className="w-80 bg-slate-800 border-l border-slate-700 overflow-y-auto">
          <div className="p-4">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">
              Series ({series.length})
            </h3>
            <div className="space-y-3">
              {series.map((s, index) => (
                <div
                  key={s.SeriesInstanceUID}
                  onClick={() => handleSeriesClick(index)}
                  className={`
                    p-3 rounded-lg cursor-pointer transition-all
                    ${index === currentSeriesIndex
                      ? 'bg-medical-500/20 border border-medical-500'
                      : 'bg-slate-700/50 border border-slate-600 hover:bg-slate-700'
                    }
                  `}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-slate-100">
                      Series {s.SeriesNumber || index + 1}
                    </span>
                    <span className="text-xs px-2 py-1 bg-medical-500/30 text-medical-300 rounded">
                      {s.Modality}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mb-2">
                    {s.SeriesDescription || 'No description'}
                  </p>
                  <div className="flex items-center gap-1 text-xs text-slate-500">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
                    </svg>
                    <span>{s.NumberOfSeriesRelatedInstances} images</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OHIFViewer;
