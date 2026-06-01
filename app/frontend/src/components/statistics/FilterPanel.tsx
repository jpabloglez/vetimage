/**
 * Advanced Filter Panel for Statistics Page
 *
 * Provides comprehensive filtering options including:
 * - Date range selection
 * - Model selection (dropdown)
 * - Status filtering (dropdown)
 * - Modality filtering (dropdown)
 * - Patient demographics
 * - DICOM metadata (body part)
 */

import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Calendar,
  Filter,
  X,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Check,
} from 'lucide-react';
import { Button } from '../ui';
import { apiClient, StatisticsFilters, StatisticsFilterOptions } from '../../utils/api';

/* ------------------------------------------------------------------ */
/*  Multi-select dropdown                                              */
/* ------------------------------------------------------------------ */

interface MultiSelectDropdownProps {
  label: string;
  options: { value: string; label: string }[];
  selected: string[];
  onChange: (selected: string[]) => void;
  placeholder?: string;
}

const MultiSelectDropdown: React.FC<MultiSelectDropdownProps> = ({
  label,
  options,
  selected,
  onChange,
  placeholder = 'All',
}) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggle = (value: string) => {
    onChange(
      selected.includes(value)
        ? selected.filter((v) => v !== value)
        : [...selected, value],
    );
  };

  const summary =
    selected.length === 0
      ? placeholder
      : selected.length <= 2
        ? selected.join(', ')
        : `${selected.length} selected`;

  return (
    <div ref={ref} className="relative flex-1 min-w-0">
      <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
        {label}
      </label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white hover:border-medical-400 focus:ring-2 focus:ring-medical-500 focus:border-transparent transition-colors"
      >
        <span className="truncate">{summary}</span>
        <ChevronDown className={`w-4 h-4 shrink-0 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute z-30 mt-1 w-full max-h-56 overflow-y-auto rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 shadow-lg">
          {options.map((opt) => {
            const isSelected = selected.includes(opt.value);
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => toggle(opt.value)}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors ${
                  isSelected
                    ? 'bg-medical-50 dark:bg-medical-900/20 text-medical-700 dark:text-medical-300'
                    : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                }`}
              >
                <span className={`w-4 h-4 shrink-0 flex items-center justify-center rounded border ${
                  isSelected
                    ? 'bg-medical-500 border-medical-500 text-white'
                    : 'border-slate-300 dark:border-slate-500'
                }`}>
                  {isSelected && <Check className="w-3 h-3" />}
                </span>
                <span className="truncate">{opt.label}</span>
              </button>
            );
          })}
          {options.length === 0 && (
            <div className="px-3 py-2 text-sm text-slate-400">No options</div>
          )}
        </div>
      )}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  FilterPanel                                                        */
/* ------------------------------------------------------------------ */

interface FilterPanelProps {
  filters: StatisticsFilters;
  onFiltersChange: (filters: StatisticsFilters) => void;
  onApply: () => void;
  onReset: () => void;
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  onFiltersChange,
  onApply,
  onReset,
}) => {
  const { t } = useTranslation('statistics');
  const [isExpanded, setIsExpanded] = useState(true);
  const [filterOptions, setFilterOptions] = useState<StatisticsFilterOptions | null>(null);
  const [isLoadingOptions, setIsLoadingOptions] = useState(true);

  // Fetch available filter options on mount
  useEffect(() => {
    const fetchOptions = async () => {
      try {
        const options = await apiClient.getStatisticsFilterOptions();
        setFilterOptions(options);
      } catch (error) {
        console.error('Failed to fetch filter options:', error);
      } finally {
        setIsLoadingOptions(false);
      }
    };

    fetchOptions();
  }, []);

  const handleDateFromChange = (value: string) => {
    onFiltersChange({ ...filters, date_from: value || null });
  };

  const handleDateToChange = (value: string) => {
    onFiltersChange({ ...filters, date_to: value || null });
  };

  const handleBodyPartChange = (bodyPart: string, checked: boolean) => {
    const currentBodyParts = filters.body_parts || [];
    const newBodyParts = checked
      ? [...currentBodyParts, bodyPart]
      : currentBodyParts.filter((bp) => bp !== bodyPart);
    onFiltersChange({ ...filters, body_parts: newBodyParts });
  };

  const handlePatientSexChange = (sex: string, checked: boolean) => {
    const currentSex = filters.patient_sex || [];
    const newSex = checked
      ? [...currentSex, sex]
      : currentSex.filter((s) => s !== sex);
    onFiltersChange({ ...filters, patient_sex: newSex });
  };

  const activeFiltersCount = [
    filters.date_from,
    filters.date_to,
    ...(filters.model_keys || []),
    ...(filters.statuses || []),
    ...(filters.modalities || []),
    ...(filters.body_parts || []),
    ...(filters.patient_sex || []),
  ].filter(Boolean).length;

  return (
    <div className="medical-card p-6 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-medical-500" />
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            {t('filters.title')}
          </h2>
          {activeFiltersCount > 0 && (
            <span className="px-2 py-1 bg-medical-100 dark:bg-medical-900/30 text-medical-700 dark:text-medical-400 text-xs font-medium rounded-full">
              {activeFiltersCount} active
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            disabled={activeFiltersCount === 0}
          >
            <X className="w-4 h-4 mr-1" />
            {t('filters.clear')}
          </Button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded"
          >
            {isExpanded ? (
              <ChevronUp className="w-5 h-5 text-slate-600 dark:text-slate-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-slate-600 dark:text-slate-400" />
            )}
          </button>
        </div>
      </div>

      {/* Filter Content */}
      {isExpanded && (
        <div className="space-y-6">
          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              <Calendar className="w-4 h-4 inline mr-1" />
              {t('filters.dateFrom')} / {t('filters.dateTo')}
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  {t('filters.dateFrom')}
                </label>
                <input
                  type="date"
                  value={filters.date_from || ''}
                  onChange={(e) => handleDateFromChange(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-medical-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  {t('filters.dateTo')}
                </label>
                <input
                  type="date"
                  value={filters.date_to || ''}
                  onChange={(e) => handleDateToChange(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-medical-500 focus:border-transparent"
                />
              </div>
            </div>
          </div>

          {/* Body Parts */}
          {!isLoadingOptions && filterOptions && filterOptions.body_parts.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                {t('filters.bodyParts')}
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {filterOptions.body_parts.map((bodyPart) => (
                  <label
                    key={bodyPart}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={(filters.body_parts || []).includes(bodyPart)}
                      onChange={(e) => handleBodyPartChange(bodyPart, e.target.checked)}
                      className="rounded border-slate-300 dark:border-slate-600 text-medical-500 focus:ring-medical-500"
                    />
                    <span className="text-sm text-slate-700 dark:text-slate-300">
                      {bodyPart}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Patient Sex */}
          {!isLoadingOptions && filterOptions && filterOptions.patient_sex.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                {t('filters.patientSex')}
              </label>
              <div className="flex gap-4">
                {filterOptions.patient_sex.map((sex) => (
                  <label
                    key={sex}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={(filters.patient_sex || []).includes(sex)}
                      onChange={(e) => handlePatientSexChange(sex, e.target.checked)}
                      className="rounded border-slate-300 dark:border-slate-600 text-medical-500 focus:ring-medical-500"
                    />
                    <span className="text-sm text-slate-700 dark:text-slate-300">
                      {sex}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Patient Age Range */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              {t('filters.ageRange')}
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  {t('filters.ageMin')}
                </label>
                <input
                  type="number"
                  min="0"
                  max="120"
                  value={filters.patient_age_min || ''}
                  onChange={(e) =>
                    onFiltersChange({
                      ...filters,
                      patient_age_min: e.target.value ? parseInt(e.target.value) : null,
                    })
                  }
                  placeholder="0"
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-medical-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  {t('filters.ageMax')}
                </label>
                <input
                  type="number"
                  min="0"
                  max="120"
                  value={filters.patient_age_max || ''}
                  onChange={(e) =>
                    onFiltersChange({
                      ...filters,
                      patient_age_max: e.target.value ? parseInt(e.target.value) : null,
                    })
                  }
                  placeholder="120"
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-medical-500 focus:border-transparent"
                />
              </div>
            </div>
          </div>

          {/* AI Models / Status / Modality — dropdown row */}
          {!isLoadingOptions && filterOptions && (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                {t('filters.title')}
              </label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {filterOptions.models.length > 0 && (
                  <MultiSelectDropdown
                    label={t('filters.models')}
                    options={filterOptions.models.map((m) => ({
                      value: m.key,
                      label: `${m.name} (${m.type})`,
                    }))}
                    selected={filters.model_keys || []}
                    onChange={(keys) => onFiltersChange({ ...filters, model_keys: keys })}
                    placeholder={t('common:labels.all')}
                  />
                )}
                {filterOptions.statuses.length > 0 && (
                  <MultiSelectDropdown
                    label={t('filters.statuses')}
                    options={filterOptions.statuses.map((s) => ({ value: s, label: s }))}
                    selected={filters.statuses || []}
                    onChange={(vals) => onFiltersChange({ ...filters, statuses: vals })}
                    placeholder={t('common:labels.all')}
                  />
                )}
                {filterOptions.modalities.length > 0 && (
                  <MultiSelectDropdown
                    label={t('filters.modalities')}
                    options={filterOptions.modalities.map((m) => ({ value: m, label: m }))}
                    selected={filters.modalities || []}
                    onChange={(vals) => onFiltersChange({ ...filters, modalities: vals })}
                    placeholder={t('common:labels.all')}
                  />
                )}
              </div>
            </div>
          )}

          {/* Apply Button */}
          <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
            <Button variant="medical" onClick={onApply} fullWidth>
              <RefreshCw className="w-4 h-4 mr-2" />
              {t('filters.apply')}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FilterPanel;
