/**
 * Metadata Viewer Component
 *
 * Displays extracted medical image metadata in a user-friendly format.
 * Adapts display based on image format (DICOM, NIfTI, or standard image).
 */

import React from 'react';
import { FileText, Image as ImageIcon, Info, Layers, Ruler, Compass } from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import { getFormatName, getFormatIcon } from '../../utils/fileValidation';

interface MetadataViewerProps {
  metadata: Record<string, any>;
  filename?: string;
}

const MetadataField: React.FC<{
  label: string;
  value: string | number | null | undefined;
  icon?: React.ReactNode;
}> = ({ label, value, icon }) => {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  return (
    <div className="flex items-start gap-2">
      {icon && <div className="text-medical-500 mt-0.5">{icon}</div>}
      <div className="flex-1">
        <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">
          {label}
        </dt>
        <dd className="text-sm font-semibold text-slate-900 dark:text-slate-100 mt-0.5">
          {value}
        </dd>
      </div>
    </div>
  );
};

const MetadataSection: React.FC<{
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}> = ({ title, icon, children }) => {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-200 dark:border-slate-700">
        {icon}
        <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          {title}
        </h4>
      </div>
      <dl className="space-y-3">
        {children}
      </dl>
    </div>
  );
};

export const MetadataViewer: React.FC<MetadataViewerProps> = ({ metadata, filename }) => {
  const format = metadata.format || 'unknown';
  const dimensions = metadata.dimensions || {};
  const voxelSize = metadata.voxel_size || {};

  // Format dimension string
  const getDimensionString = () => {
    if (dimensions.depth && dimensions.depth > 1) {
      return `${dimensions.width} × ${dimensions.height} × ${dimensions.depth}`;
    }
    return `${dimensions.width || 0} × ${dimensions.height || 0}`;
  };

  // Format voxel size string
  const getVoxelSizeString = () => {
    if (voxelSize.z) {
      return `${voxelSize.x?.toFixed(2)} × ${voxelSize.y?.toFixed(2)} × ${voxelSize.z?.toFixed(2)} mm`;
    } else if (voxelSize.x && voxelSize.y) {
      return `${voxelSize.x?.toFixed(2)} × ${voxelSize.y?.toFixed(2)} mm`;
    }
    return null;
  };

  // Determine if 2D or 3D
  const is3D = dimensions.depth && dimensions.depth > 1;

  return (
    <Card variant="medical" className="h-full">
      <CardHeader>
        <div className="flex items-center gap-2">
          <div className="text-2xl">{getFormatIcon(format)}</div>
          <div className="flex-1">
            <CardTitle>Image Characteristics</CardTitle>
            {filename && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 truncate">
                {filename}
              </p>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Core Information */}
        <MetadataSection title="Core Information" icon={<Info className="h-4 w-4 text-medical-500" />}>
          <MetadataField
            label="Format"
            value={getFormatName(format)}
            icon={<FileText className="h-4 w-4" />}
          />
          <MetadataField
            label="Modality"
            value={metadata.modality || 'Unknown'}
            icon={<ImageIcon className="h-4 w-4" />}
          />
          {metadata.anatomical_region && (
            <MetadataField
              label="Anatomical Region"
              value={metadata.anatomical_region}
            />
          )}
        </MetadataSection>

        {/* Dimensions */}
        {(dimensions.width || dimensions.height) && (
          <MetadataSection title="Dimensions" icon={<Layers className="h-4 w-4 text-medical-500" />}>
            <MetadataField
              label={is3D ? "Volume Size (W × H × D)" : "Image Size (W × H)"}
              value={getDimensionString()}
              icon={<Ruler className="h-4 w-4" />}
            />
            {voxelSize.x && (
              <MetadataField
                label="Voxel/Pixel Spacing"
                value={getVoxelSizeString()}
              />
            )}
            {metadata.orientation && (
              <MetadataField
                label="Orientation"
                value={metadata.orientation}
                icon={<Compass className="h-4 w-4" />}
              />
            )}
            {dimensions.time_points && (
              <MetadataField
                label="Time Points"
                value={dimensions.time_points}
              />
            )}
          </MetadataSection>
        )}

        {/* Format-specific metadata */}
        {format === 'dicom' && (
          <MetadataSection title="DICOM Details">
            {metadata.study_description && (
              <MetadataField
                label="Study Description"
                value={metadata.study_description}
              />
            )}
            {metadata.series_description && (
              <MetadataField
                label="Series Description"
                value={metadata.series_description}
              />
            )}
            {metadata.patient_position && (
              <MetadataField
                label="Patient Position"
                value={metadata.patient_position}
              />
            )}
            {metadata.acquisition_date && (
              <MetadataField
                label="Acquisition Date"
                value={metadata.acquisition_date}
              />
            )}
          </MetadataSection>
        )}

        {format === 'nifti' && (
          <MetadataSection title="NIfTI Details">
            {metadata.data_type && (
              <MetadataField
                label="Data Type"
                value={metadata.data_type}
              />
            )}
            {metadata.description && (
              <MetadataField
                label="Description"
                value={metadata.description}
              />
            )}
            {metadata.qform_code !== null && metadata.qform_code !== undefined && (
              <MetadataField
                label="QForm Code"
                value={metadata.qform_code}
              />
            )}
            {metadata.sform_code !== null && metadata.sform_code !== undefined && (
              <MetadataField
                label="SForm Code"
                value={metadata.sform_code}
              />
            )}
          </MetadataSection>
        )}

        {format === 'image' && (
          <MetadataSection title="Image Details">
            {metadata.color_mode && (
              <MetadataField
                label="Color Mode"
                value={metadata.color_mode}
              />
            )}
            {metadata.file_format && (
              <MetadataField
                label="File Format"
                value={metadata.file_format}
              />
            )}
            {metadata.exif && Object.keys(metadata.exif).length > 0 && (
              <div className="text-xs text-slate-500 dark:text-slate-400">
                <p>EXIF data available ({Object.keys(metadata.exif).length} fields)</p>
              </div>
            )}
          </MetadataSection>
        )}

        {/* Technical Summary */}
        <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
          <div className="grid grid-cols-2 gap-4 text-center">
            <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <p className="text-xs text-slate-500 dark:text-slate-400">Type</p>
              <p className="text-lg font-semibold text-medical-600 dark:text-medical-400">
                {is3D ? '3D' : '2D'}
              </p>
            </div>
            <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <p className="text-xs text-slate-500 dark:text-slate-400">Pixels</p>
              <p className="text-lg font-semibold text-medical-600 dark:text-medical-400">
                {dimensions.width && dimensions.height
                  ? `${((dimensions.width * dimensions.height * (dimensions.depth || 1)) / 1000000).toFixed(1)}M`
                  : 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default MetadataViewer;
