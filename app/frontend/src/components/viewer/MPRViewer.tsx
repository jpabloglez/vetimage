/**
 * MPR (Multi-Planar Reconstruction) Viewer
 *
 * Three-panel view showing axial, sagittal, and coronal planes.
 * Only applicable for volumetric data (CT/MR with sufficient slices).
 */

import React, { useState } from 'react';
import { Maximize2, Minimize2 } from 'lucide-react';

interface MPRViewerProps {
  studyInstanceUID: string;
  seriesInstanceUID: string;
  totalSlices: number;
}

type Plane = 'axial' | 'sagittal' | 'coronal';

const planeLabels: Record<Plane, string> = {
  axial: 'Axial',
  sagittal: 'Sagittal',
  coronal: 'Coronal',
};

const planeColors: Record<Plane, string> = {
  axial: 'border-blue-500',
  sagittal: 'border-green-500',
  coronal: 'border-red-500',
};

export const MPRViewer: React.FC<MPRViewerProps> = ({
  studyInstanceUID,
  seriesInstanceUID,
  totalSlices,
}) => {
  const [maximizedPlane, setMaximizedPlane] = useState<Plane | null>(null);
  const [sliceIndices, setSliceIndices] = useState<Record<Plane, number>>({
    axial: Math.floor(totalSlices / 2),
    sagittal: 128,
    coronal: 128,
  });

  const planes: Plane[] = ['axial', 'sagittal', 'coronal'];

  if (totalSlices < 10) {
    return (
      <div className="flex items-center justify-center h-64 bg-slate-800 rounded-lg">
        <p className="text-slate-400 text-sm">
          MPR requires volumetric data with at least 10 slices.
          This series has {totalSlices} slice(s).
        </p>
      </div>
    );
  }

  const handleSliceChange = (plane: Plane, value: number) => {
    setSliceIndices((prev) => ({ ...prev, [plane]: value }));
  };

  const renderViewport = (plane: Plane) => {
    const isMaximized = maximizedPlane === plane;
    const isHidden = maximizedPlane !== null && maximizedPlane !== plane;

    if (isHidden) return null;

    return (
      <div
        key={plane}
        className={`relative bg-black rounded-lg overflow-hidden border-2 ${planeColors[plane]} ${
          isMaximized ? 'col-span-3 row-span-2' : ''
        }`}
      >
        {/* Plane Label */}
        <div className="absolute top-2 left-2 z-10 flex items-center gap-2">
          <span className="px-2 py-1 bg-slate-800/80 backdrop-blur-sm text-xs font-semibold text-white rounded">
            {planeLabels[plane]}
          </span>
          <button
            onClick={() => setMaximizedPlane(isMaximized ? null : plane)}
            className="p-1 bg-slate-800/80 backdrop-blur-sm rounded hover:bg-slate-700/80 transition-colors"
          >
            {isMaximized ? (
              <Minimize2 className="w-3 h-3 text-white" />
            ) : (
              <Maximize2 className="w-3 h-3 text-white" />
            )}
          </button>
        </div>

        {/* Placeholder viewport */}
        <div className="w-full h-full min-h-[250px] flex items-center justify-center">
          <div className="text-center text-slate-500">
            <p className="text-sm font-medium">{planeLabels[plane]} View</p>
            <p className="text-xs mt-1">Slice {sliceIndices[plane]}</p>
          </div>
        </div>

        {/* Slice Slider */}
        <div className="absolute bottom-2 left-2 right-2">
          <input
            type="range"
            min={0}
            max={plane === 'axial' ? totalSlices - 1 : 255}
            value={sliceIndices[plane]}
            onChange={(e) => handleSliceChange(plane, parseInt(e.target.value))}
            className="w-full h-1 bg-slate-600 rounded-lg appearance-none cursor-pointer accent-medical-500"
          />
        </div>
      </div>
    );
  };

  return (
    <div className={`grid gap-2 h-full ${maximizedPlane ? 'grid-cols-1' : 'grid-cols-3'}`}>
      {planes.map(renderViewport)}
    </div>
  );
};

export default MPRViewer;
