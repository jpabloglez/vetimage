/**
 * Model Recommendation Component
 *
 * Displays AI model recommendations based on uploaded image characteristics.
 * Shows compatibility scores, match reasons, and warnings.
 * Allows user to select a model for analysis.
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Brain, CheckCircle, AlertTriangle, ChevronDown, ChevronUp, Sparkles, Award, XCircle } from 'lucide-react';
import { apiClient, ScoredModel, AIModel } from '../../utils/api';
import Card, { CardContent } from '../ui/Card';
import Button from '../ui/Button';
import toast from 'react-hot-toast';

interface ModelRecommendationProps {
  imageId: number;
  onModelSelect: (model: AIModel, isRecommended: boolean) => void;
}

const CompatibilityBadge: React.FC<{ score: number }> = ({ score }) => {
  const getColor = () => {
    if (score >= 80) return 'bg-success-100 text-success-700 dark:bg-success-900 dark:text-success-300';
    if (score >= 50) return 'bg-warning-100 text-warning-700 dark:bg-warning-900 dark:text-warning-300';
    return 'bg-error-100 text-error-700 dark:bg-error-900 dark:text-error-300';
  };

  const getLabel = () => {
    if (score >= 80) return 'Excellent Match';
    if (score >= 50) return 'Good Match';
    if (score >= 30) return 'Possible Match';
    return 'Not Compatible';
  };

  return (
    <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${getColor()}`}>
      <Sparkles className="h-3 w-3" />
      {score}% - {getLabel()}
    </div>
  );
};

const ModelCard: React.FC<{
  scoredModel: ScoredModel;
  onSelect: (model: AIModel) => void;
  isRecommended?: boolean;
}> = ({ scoredModel, onSelect, isRecommended }) => {
  const [expanded, setExpanded] = useState(false);
  const { model, compatibility_score, match_reasons, warnings } = scoredModel;
  const isIncompatible = compatibility_score < 30;

  return (
    <Card className={`relative overflow-hidden hover:shadow-lg transition-shadow ${isIncompatible ? 'opacity-75' : ''}`}>
      {isRecommended && (
        <div className="absolute top-0 right-0 bg-gradient-to-l from-medical-500 to-medical-400 text-white px-3 py-1 text-xs font-semibold rounded-bl-lg flex items-center gap-1">
          <Award className="h-3 w-3" />
          RECOMMENDED
        </div>
      )}

      <CardContent className="p-4">
        {/* Header */}
        <div className="mb-3">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-medical-100 dark:bg-medical-900 rounded-lg">
              <Brain className="h-5 w-5 text-medical-600 dark:text-medical-400" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                {model.name}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {model.model_type} • v{model.version}
              </p>
            </div>
          </div>

          <div className="mt-3">
            <CompatibilityBadge score={compatibility_score} />
          </div>
        </div>

        {/* Not Compatible Banner */}
        {isIncompatible && (
          <div className="mb-3 flex items-center gap-2 px-3 py-2 bg-error-50 dark:bg-error-900/30 border border-error-200 dark:border-error-800 rounded-lg">
            <XCircle className="h-4 w-4 text-error-500 flex-shrink-0" />
            <span className="text-sm font-medium text-error-700 dark:text-error-400">
              Not Compatible with this image
            </span>
          </div>
        )}

        {/* Description */}
        <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2 mb-3">
          {model.description}
        </p>

        {/* Match Reasons */}
        {match_reasons.length > 0 && (
          <div className="mb-3 space-y-1">
            {match_reasons.map((reason, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs">
                <CheckCircle className="h-3 w-3 text-success-500 mt-0.5 flex-shrink-0" />
                <span className="text-slate-600 dark:text-slate-400">{reason}</span>
              </div>
            ))}
          </div>
        )}

        {/* Warnings */}
        {warnings.length > 0 && (
          <div className="mb-3 space-y-1">
            {warnings.map((warning, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs">
                <AlertTriangle className="h-3 w-3 text-warning-500 mt-0.5 flex-shrink-0" />
                <span className="text-warning-700 dark:text-warning-400">{warning}</span>
              </div>
            ))}
          </div>
        )}

        {/* Expandable Details */}
        {model.organization && (
          <div className="pt-3 border-t border-slate-200 dark:border-slate-700">
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center justify-between w-full text-sm text-medical-600 dark:text-medical-400 hover:text-medical-700 dark:hover:text-medical-300"
            >
              <span>Model Details</span>
              {expanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>

            {expanded && (
              <div className="mt-3 space-y-2 text-xs text-slate-600 dark:text-slate-400">
                {model.organization && (
                  <div>
                    <span className="font-semibold">Organization:</span> {model.organization}
                  </div>
                )}
                {model.supported_modalities && model.supported_modalities.length > 0 && (
                  <div>
                    <span className="font-semibold">Supported Modalities:</span>{' '}
                    {model.supported_modalities.join(', ')}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Select Button */}
        <Button
          variant="medical"
          fullWidth
          className="mt-4"
          onClick={() => onSelect(model)}
          disabled={isIncompatible}
        >
          {isIncompatible ? 'Not Compatible' : 'Select This Model'}
        </Button>
      </CardContent>
    </Card>
  );
};

const INPUT_CLS =
  'w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-medical-500 focus:border-medical-500 outline-none';

export const ModelRecommendation: React.FC<ModelRecommendationProps> = ({
  imageId,
  onModelSelect,
}) => {
  const { t } = useTranslation('analyze');
  const [recommendations, setRecommendations] = useState<ScoredModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRecommendations();
  }, [imageId]);

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getModelRecommendations(imageId);
      setRecommendations(response.recommended_models);

      if (response.recommended_models.length === 0) {
        toast('No compatible models found for this image', { icon: 'ℹ️' });
      } else {
        toast.success(`Found ${response.recommended_models.length} compatible model(s)`);
      }
    } catch (err: any) {
      console.error('Failed to fetch recommendations:', err);
      setError(err.message || 'Failed to load model recommendations');
      toast.error('Failed to load model recommendations');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medical-500 mx-auto mb-4" />
          <p className="text-slate-600 dark:text-slate-400">
            Finding compatible AI models...
          </p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <AlertTriangle className="h-12 w-12 text-error-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            Error Loading Recommendations
          </h3>
          <p className="text-slate-600 dark:text-slate-400 mb-4">{error}</p>
          <Button onClick={fetchRecommendations}>Try Again</Button>
        </CardContent>
      </Card>
    );
  }

  if (recommendations.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Brain className="h-16 w-16 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            No Compatible Models Found
          </h3>
          <p className="text-slate-600 dark:text-slate-400">
            No AI models are currently available that match your image characteristics.
          </p>
        </CardContent>
      </Card>
    );
  }

  const topModel = recommendations[0];
  const otherModels = recommendations.slice(1);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-medical-500" />
        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
          Recommended Model
        </h2>
      </div>

      {/* Top Recommended Card */}
      <ModelCard
        scoredModel={topModel}
        onSelect={(model) => onModelSelect(model, true)}
        isRecommended
      />

      {/* Dropdown for other models */}
      {otherModels.length > 0 && (
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            Other available models
          </label>
          <select
            className={INPUT_CLS}
            defaultValue=""
            disabled={loading}
            onChange={(e) => {
              const key = e.target.value;
              if (!key) return;
              const found = otherModels.find((r) => r.model.key === key);
              if (found) onModelSelect(found.model, false);
              e.target.value = '';
            }}
          >
            <option value="" disabled>
              {t('selectOtherModel')}
            </option>
            {otherModels.map((r) => (
              <option key={r.model.key} value={r.model.key}>
                {r.model.name} v{r.model.version} — {r.compatibility_score}%
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
};

export default ModelRecommendation;
