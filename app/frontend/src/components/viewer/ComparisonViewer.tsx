/**
 * Side-by-Side Comparison Viewer
 *
 * Two synchronized viewports for comparing studies from the same patient.
 */

import React, { useState } from 'react';
import { Columns2, ArrowLeftRight } from 'lucide-react';

interface ComparisonViewerProps {
  leftStudyUID: string;
  rightStudyUID: string;
  onSwap?: () => void;
}

export const ComparisonViewer: React.FC<ComparisonViewerProps> = ({
  leftStudyUID,
  rightStudyUID,
  onSwap,
}) => {
  const [syncScroll, setSyncScroll] = useState(true);
  const [syncZoom, setSyncZoom] = useState(true);

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <Columns2 className="w-5 h-5 text-medical-400" />
          <span className="text-sm font-medium text-slate-200">Comparison View</span>
        </div>

        <div className="flex items-center gap-4">
          {/* Sync toggles */}
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={syncScroll}
              onChange={(e) => setSyncScroll(e.target.checked)}
              className="rounded border-slate-600 bg-slate-700 text-medical-500 focus:ring-medical-500"
            />
            Sync Scroll
          </label>
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={syncZoom}
              onChange={(e) => setSyncZoom(e.target.checked)}
              className="rounded border-slate-600 bg-slate-700 text-medical-500 focus:ring-medical-500"
            />
            Sync Zoom
          </label>

          {/* Swap button */}
          {onSwap && (
            <button
              onClick={onSwap}
              className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400 hover:text-white bg-slate-700 hover:bg-slate-600 rounded transition-colors"
            >
              <ArrowLeftRight className="w-3 h-3" />
              Swap
            </button>
          )}
        </div>
      </div>

      {/* Viewports */}
      <div className="flex flex-1 min-h-0">
        {/* Left Viewport */}
        <div className="flex-1 border-r border-slate-700 relative">
          <div className="absolute top-2 left-2 z-10">
            <span className="px-2 py-1 bg-blue-500/80 text-white text-xs font-semibold rounded">
              Study A
            </span>
          </div>
          <div className="w-full h-full flex items-center justify-center bg-black">
            <div className="text-center text-slate-500">
              <p className="text-sm">Left viewport</p>
              <p className="text-xs mt-1 font-mono">{leftStudyUID.slice(0, 20)}...</p>
            </div>
          </div>
        </div>

        {/* Right Viewport */}
        <div className="flex-1 relative">
          <div className="absolute top-2 left-2 z-10">
            <span className="px-2 py-1 bg-green-500/80 text-white text-xs font-semibold rounded">
              Study B
            </span>
          </div>
          <div className="w-full h-full flex items-center justify-center bg-black">
            <div className="text-center text-slate-500">
              <p className="text-sm">Right viewport</p>
              <p className="text-xs mt-1 font-mono">{rightStudyUID.slice(0, 20)}...</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ComparisonViewer;
