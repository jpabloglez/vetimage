/**
 * Tools Page
 *
 * Card-based launcher for DICOM utilities:
 * - Viewer: Browse studies and open the OHIF viewer
 * - Anonymizer: Remove PHI from DICOM files with CSV metadata export
 * - Converter: Convert DICOM to NIfTI, JPG, PNG
 * - Compressor: Archive to 7z with CSV study info
 * - Tag Editor: View and modify DICOM metadata
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Eye,
  ShieldCheck,
  FileOutput,
  Archive,
  Tags,
  ArrowLeft,
  ChevronRight,
  Wrench,
} from 'lucide-react';
import DicomDropzone from '../components/uploader/DicomDropzone';
import StudyBrowser from '../components/viewer/StudyBrowser';
import OHIFViewer from '../components/viewer/OHIFViewer';
import AnonymizationPanel from '../components/anonymization/AnonymizationPanel';
import DicomTagEditor from '../components/tags/DicomTagEditor';
import ConversionPanel from '../components/conversion/ConversionPanel';
import PageHeader from '../components/ui/PageHeader';
import Button from '../components/ui/Button';

type ActiveTool = null | 'viewer' | 'anonymize' | 'convert' | 'compress' | 'tags';

interface ToolCard {
  key: ActiveTool & string;
  nameKey: string;
  descKey: string;
  icon: React.ElementType;
  color: string;
  badgeKey?: string;
}

const TOOLS: ToolCard[] = [
  {
    key: 'viewer',
    nameKey: 'viewer.title',
    descKey: 'viewer.description',
    icon: Eye,
    color: 'from-blue-500 to-blue-600',
  },
  {
    key: 'anonymize',
    nameKey: 'anonymizer.title',
    descKey: 'anonymizer.description',
    icon: ShieldCheck,
    color: 'from-emerald-500 to-emerald-600',
  },
  {
    key: 'convert',
    nameKey: 'converter.title',
    descKey: 'converter.description',
    icon: FileOutput,
    color: 'from-violet-500 to-violet-600',
  },
  {
    key: 'compress',
    nameKey: 'compressor.title',
    descKey: 'compressor.description',
    icon: Archive,
    color: 'from-amber-500 to-amber-600',
    badgeKey: 'comingSoon',
  },
  {
    key: 'tags',
    nameKey: 'tagEditor.title',
    descKey: 'tagEditor.description',
    icon: Tags,
    color: 'from-rose-500 to-rose-600',
  },
];

const ToolsPage: React.FC = () => {
  const { t } = useTranslation('tools');
  const [activeTool, setActiveTool] = useState<ActiveTool>(null);
  const [selectedStudyUID, setSelectedStudyUID] = useState<string | null>(null);
  const [viewerMode, setViewerMode] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Full-screen OHIF viewer
  if (viewerMode && selectedStudyUID) {
    return (
      <OHIFViewer
        studyInstanceUIDs={[selectedStudyUID]}
        onClose={() => {
          setViewerMode(false);
          setSelectedStudyUID(null);
        }}
      />
    );
  }

  const handleUploadComplete = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  // Active tool view
  if (activeTool) {
    const tool = TOOLS.find((t) => t.key === activeTool)!;
    const Icon = tool.icon;

    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 pt-20">
        <div className="container mx-auto px-4 py-8 max-w-7xl">
          {/* Back + Title */}
          <div className="flex items-center gap-4 mb-8">
            <Button
              variant="ghost"
              size="sm"
              leftIcon={ArrowLeft}
              onClick={() => setActiveTool(null)}
            >
              {t('backToTools')}
            </Button>
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${tool.color} flex items-center justify-center`}>
                <Icon className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                  {t(tool.nameKey)}
                </h1>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {t(tool.descKey)}
                </p>
              </div>
            </div>
          </div>

          {/* Tool Content */}
          {activeTool === 'viewer' && (
            <div className="space-y-8">
              <div className="max-w-4xl mx-auto">
                <DicomDropzone onUploadComplete={handleUploadComplete} />
              </div>
              <StudyBrowser
                onStudySelect={(uid) => {
                  setSelectedStudyUID(uid);
                  setViewerMode(true);
                }}
                refreshTrigger={refreshTrigger}
              />
            </div>
          )}

          {activeTool === 'anonymize' && (
            <div className="max-w-4xl mx-auto">
              <AnonymizationPanel />
            </div>
          )}

          {activeTool === 'convert' && (
            <div className="max-w-4xl mx-auto">
              <ConversionPanel />
            </div>
          )}

          {activeTool === 'compress' && (
            <div className="max-w-4xl mx-auto">
              <div className="medical-card p-12 text-center">
                <Archive className="w-16 h-16 mx-auto mb-4 text-amber-400" />
                <h3 className="text-xl font-semibold mb-2 text-slate-900 dark:text-slate-100">
                  {t('compressor.title')} — {t('comingSoon')}
                </h3>
                <p className="text-slate-600 dark:text-slate-400 max-w-md mx-auto">
                  {t('compressor.description')}
                </p>
              </div>
            </div>
          )}

          {activeTool === 'tags' && (
            <div className="max-w-6xl mx-auto">
              <DicomTagEditor imageId={null} />
            </div>
          )}
        </div>
      </div>
    );
  }

  // Card grid (home state)
  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <PageHeader icon={Wrench} title={t('title')} subtitle={t('subtitle')} />

      {/* Tool Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {TOOLS.map((tool) => {
            const Icon = tool.icon;
            const isDisabled = !!tool.badgeKey;

            return (
              <button
                key={tool.key}
                onClick={() => !isDisabled && setActiveTool(tool.key)}
                disabled={isDisabled}
                className={`
                  group relative text-left p-6 rounded-2xl border transition-all duration-200
                  ${isDisabled
                    ? 'bg-slate-100 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 opacity-75 cursor-not-allowed'
                    : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-medical-300 dark:hover:border-medical-600 hover:shadow-lg hover:-translate-y-0.5 cursor-pointer'
                  }
                `}
              >
                {/* Badge */}
                {tool.badgeKey && (
                  <span className="absolute top-4 right-4 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
                    {t(tool.badgeKey)}
                  </span>
                )}

                {/* Icon */}
                <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${tool.color} flex items-center justify-center mb-5 shadow-lg shadow-black/10`}>
                  <Icon className="w-7 h-7 text-white" />
                </div>

                {/* Content */}
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  {t(tool.nameKey)}
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                  {t(tool.descKey)}
                </p>

                {/* Arrow */}
                {!isDisabled && (
                  <div className="flex items-center text-sm font-medium text-medical-600 dark:text-medical-400 opacity-0 group-hover:opacity-100 transition-opacity">
                    {t('openTool')}
                    <ChevronRight className="w-4 h-4 ml-1 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                )}
              </button>
            );
          })}
      </div>
    </div>
  );
};

export default ToolsPage;
