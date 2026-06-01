/**
 * ModelCard Component
 *
 * Displays AI model information in a card format for the model catalog.
 * Shows key information like name, type, description, and performance metrics.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent, CardFooter } from '../ui/Card';
import Button from '../ui/Button';
import { AIModel } from '../../utils/api';

export interface ModelCardProps {
  model: AIModel;
  onSelect?: (model: AIModel) => void;
}

const ModelCard: React.FC<ModelCardProps> = ({ model, onSelect }) => {
  const navigate = useNavigate();

  const handleViewDetails = () => {
    navigate(`/models/${model.key}`);
  };

  const handleSelect = () => {
    if (onSelect) {
      onSelect(model);
    }
  };

  // Format hyphen/underscore-separated strings to title case
  const formatLabel = (value: string): string =>
    value.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  // Get model type display name
  const getModelTypeDisplay = (type: string): string => {
    const typeMap: Record<string, string> = {
      'registration': 'Image Registration',
      'segmentation': 'Image Segmentation',
      'classification': 'Image Classification',
      'detection': 'Object Detection',
      'reconstruction': '3D Reconstruction',
      'other': 'Other',
    };
    return typeMap[type] || type;
  };

  // Get model type color
  const getModelTypeColor = (type: string): string => {
    const colorMap: Record<string, string> = {
      'registration': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      'segmentation': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      'classification': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      'detection': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
      'reconstruction': 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
      'other': 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
    };
    return colorMap[type] || colorMap['other'];
  };

  return (
    <Card variant="medical" className="hover:scale-[1.02] cursor-pointer group">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle>{model.name}</CardTitle>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Version {model.version}
              {model.organization && ` • ${model.organization}`}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span
              className={`px-3 py-1 rounded-full text-xs font-medium ${getModelTypeColor(model.model_type)}`}
            >
              {getModelTypeDisplay(model.model_type)}
            </span>
            {model.requires_anonymization && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                <ShieldCheck size={11} />
                Anon required
              </span>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* Description */}
        <p className="text-slate-600 dark:text-slate-300 mb-4 line-clamp-3">
          {model.description}
        </p>

        {/* Metadata: Modalities, Body Part, Clinical Context */}
        {((model.supported_modalities && model.supported_modalities.length > 0) ||
          (model.anatomical_regions && model.anatomical_regions.length > 0) ||
          (model.medical_domains && model.medical_domains.length > 0)) && (
          <div className="mt-4 space-y-2 border-t border-slate-100 dark:border-slate-700 pt-3">

            {/* Modalities */}
            {model.supported_modalities && model.supported_modalities.length > 0 && (
              <div className="flex items-start gap-2">
                <span className="text-xs text-slate-500 dark:text-slate-400 w-24 shrink-0 pt-0.5">
                  Modalities
                </span>
                <div className="flex flex-wrap gap-1">
                  {model.supported_modalities.map((modality, index) => (
                    <span
                      key={index}
                      className="px-2 py-0.5 bg-medical-500/10 text-medical-600 dark:text-medical-400 rounded text-xs font-medium"
                    >
                      {modality}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Body Part */}
            {model.anatomical_regions && model.anatomical_regions.length > 0 && (
              <div className="flex items-start gap-2">
                <span className="text-xs text-slate-500 dark:text-slate-400 w-24 shrink-0 pt-0.5">
                  Body Part
                </span>
                <div className="flex flex-wrap gap-1">
                  {model.anatomical_regions.map((region, index) => (
                    <span
                      key={index}
                      className="px-2 py-0.5 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 rounded text-xs font-medium"
                    >
                      {formatLabel(region)}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Clinical Context */}
            {model.medical_domains && model.medical_domains.length > 0 && (
              <div className="flex items-start gap-2">
                <span className="text-xs text-slate-500 dark:text-slate-400 w-24 shrink-0 pt-0.5">
                  Clinical
                </span>
                <div className="flex flex-wrap gap-1">
                  {model.medical_domains.map((domain, index) => (
                    <span
                      key={index}
                      className="px-2 py-0.5 bg-violet-50 dark:bg-violet-900/20 text-violet-700 dark:text-violet-400 rounded text-xs font-medium"
                    >
                      {formatLabel(domain)}
                    </span>
                  ))}
                </div>
              </div>
            )}

          </div>
        )}
      </CardContent>

      <CardFooter>
        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          {model.license_name && (
            <span className="flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              {model.license_name}
            </span>
          )}
          {model.download_count !== undefined && model.download_count > 0 && (
            <span className="flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              {model.download_count} uses
            </span>
          )}
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleViewDetails}
            className="group-hover:border-medical-500 group-hover:text-medical-600"
          >
            View Details
          </Button>
          {onSelect && (
            <Button
              variant="medical"
              size="sm"
              onClick={handleSelect}
            >
              Select
            </Button>
          )}
        </div>
      </CardFooter>
    </Card>
  );
};

export default ModelCard;
