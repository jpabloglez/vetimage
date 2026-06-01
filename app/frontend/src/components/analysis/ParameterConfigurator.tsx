/**
 * Parameter Configurator Component
 *
 * Dynamically generates form fields from AI model parameter schemas.
 * Pre-fills with default values and validates inputs.
 * Supports various parameter types: string, number, select, boolean, range.
 */

import React, { useState, useEffect } from 'react';
import { Settings, Info, AlertCircle, CheckCircle } from 'lucide-react';
import { AIModel } from '../../utils/api';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';

interface ParameterConfiguratorProps {
  model: AIModel;
  onParametersChange: (params: Record<string, any>, isValid: boolean) => void;
  onSubmit?: () => void;
}

interface ParameterSchema {
  type: 'string' | 'number' | 'integer' | 'boolean' | 'select' | 'range';
  label: string;
  description?: string;
  default?: any;
  required?: boolean;
  min?: number;
  max?: number;
  step?: number;
  options?: Array<{ value: string | number; label: string }>;
  pattern?: string;
  placeholder?: string;
}

interface ValidationError {
  field: string;
  message: string;
}

const ParameterField: React.FC<{
  name: string;
  schema: ParameterSchema;
  value: any;
  onChange: (value: any) => void;
  error?: string;
}> = ({ name, schema, value, onChange, error }) => {
  const renderInput = () => {
    switch (schema.type) {
      case 'boolean':
        return (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={value || false}
              onChange={(e) => onChange(e.target.checked)}
              className="w-4 h-4 text-medical-600 bg-slate-100 border-slate-300 rounded focus:ring-medical-500 dark:focus:ring-medical-600 dark:ring-offset-slate-800 focus:ring-2 dark:bg-slate-700 dark:border-slate-600"
            />
            <span className="text-sm text-slate-700 dark:text-slate-300">
              {schema.label}
            </span>
          </label>
        );

      case 'select':
        return (
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {schema.label}
              {schema.required && <span className="text-error-500 ml-1">*</span>}
            </label>
            <select
              value={value || ''}
              onChange={(e) => onChange(e.target.value)}
              className={`
                w-full px-3 py-2 text-sm border rounded-lg
                bg-white dark:bg-slate-800
                text-slate-900 dark:text-slate-100
                ${error
                  ? 'border-error-500 focus:ring-error-500'
                  : 'border-slate-300 dark:border-slate-600 focus:ring-medical-500'
                }
                focus:outline-none focus:ring-2
              `}
            >
              <option value="">Select an option...</option>
              {schema.options?.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        );

      case 'range':
        return (
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {schema.label}
              {schema.required && <span className="text-error-500 ml-1">*</span>}
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={schema.min}
                max={schema.max}
                step={schema.step || 1}
                value={value || schema.default || schema.min || 0}
                onChange={(e) => onChange(Number(e.target.value))}
                className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer dark:bg-slate-700"
              />
              <span className="text-sm font-semibold text-medical-600 dark:text-medical-400 min-w-[60px] text-right">
                {value || schema.default || schema.min || 0}
              </span>
            </div>
            {schema.min !== undefined && schema.max !== undefined && (
              <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mt-1">
                <span>{schema.min}</span>
                <span>{schema.max}</span>
              </div>
            )}
          </div>
        );

      case 'number':
      case 'integer':
        return (
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {schema.label}
              {schema.required && <span className="text-error-500 ml-1">*</span>}
            </label>
            <input
              type="number"
              min={schema.min}
              max={schema.max}
              step={schema.step || (schema.type === 'integer' ? 1 : 'any')}
              value={value || ''}
              onChange={(e) => {
                const val = e.target.value === '' ? null : Number(e.target.value);
                onChange(val);
              }}
              placeholder={schema.placeholder}
              className={`
                w-full px-3 py-2 text-sm border rounded-lg
                bg-white dark:bg-slate-800
                text-slate-900 dark:text-slate-100
                ${error
                  ? 'border-error-500 focus:ring-error-500'
                  : 'border-slate-300 dark:border-slate-600 focus:ring-medical-500'
                }
                focus:outline-none focus:ring-2
              `}
            />
          </div>
        );

      case 'string':
      default:
        return (
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {schema.label}
              {schema.required && <span className="text-error-500 ml-1">*</span>}
            </label>
            <input
              type="text"
              value={value || ''}
              onChange={(e) => onChange(e.target.value)}
              placeholder={schema.placeholder}
              className={`
                w-full px-3 py-2 text-sm border rounded-lg
                bg-white dark:bg-slate-800
                text-slate-900 dark:text-slate-100
                ${error
                  ? 'border-error-500 focus:ring-error-500'
                  : 'border-slate-300 dark:border-slate-600 focus:ring-medical-500'
                }
                focus:outline-none focus:ring-2
              `}
            />
          </div>
        );
    }
  };

  return (
    <div className="space-y-1">
      {renderInput()}
      {schema.description && !error && (
        <div className="flex items-start gap-1 text-xs text-slate-500 dark:text-slate-400">
          <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
          <span>{schema.description}</span>
        </div>
      )}
      {error && (
        <div className="flex items-start gap-1 text-xs text-error-600 dark:text-error-400">
          <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};

export const ParameterConfigurator: React.FC<ParameterConfiguratorProps> = ({
  model,
  onParametersChange,
  onSubmit,
}) => {
  const [parameters, setParameters] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isValid, setIsValid] = useState(false);

  // Initialize parameters with defaults
  useEffect(() => {
    const initialParams: Record<string, any> = {};
    const parameterSchema = model.required_parameters || {};

    Object.entries(parameterSchema).forEach(([key, schema]: [string, any]) => {
      if (model.default_parameters && key in model.default_parameters) {
        initialParams[key] = model.default_parameters[key];
      } else if (schema.default !== undefined) {
        initialParams[key] = schema.default;
      } else {
        initialParams[key] = null;
      }
    });

    setParameters(initialParams);
  }, [model]);

  // Validate parameters
  useEffect(() => {
    const newErrors: Record<string, string> = {};
    const parameterSchema = model.required_parameters || {};

    Object.entries(parameterSchema).forEach(([key, schema]: [string, any]) => {
      const value = parameters[key];

      // Required field validation
      if (schema.required && (value === null || value === undefined || value === '')) {
        newErrors[key] = 'This field is required';
        return;
      }

      // Skip validation for optional empty fields
      if (value === null || value === undefined || value === '') {
        return;
      }

      // Type-specific validation
      if (schema.type === 'number' || schema.type === 'integer') {
        const numValue = Number(value);
        if (isNaN(numValue)) {
          newErrors[key] = 'Must be a valid number';
        } else {
          if (schema.min !== undefined && numValue < schema.min) {
            newErrors[key] = `Must be at least ${schema.min}`;
          }
          if (schema.max !== undefined && numValue > schema.max) {
            newErrors[key] = `Must be at most ${schema.max}`;
          }
          if (schema.type === 'integer' && !Number.isInteger(numValue)) {
            newErrors[key] = 'Must be an integer';
          }
        }
      }

      // Pattern validation for strings
      if (schema.type === 'string' && schema.pattern) {
        const regex = new RegExp(schema.pattern);
        if (!regex.test(value)) {
          newErrors[key] = 'Invalid format';
        }
      }
    });

    setErrors(newErrors);
    const valid = Object.keys(newErrors).length === 0;
    setIsValid(valid);
    onParametersChange(parameters, valid);
  }, [parameters, model, onParametersChange]);

  const handleParameterChange = (key: string, value: any) => {
    setParameters((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const parameterSchema = model.required_parameters || {};
  const hasParameters = Object.keys(parameterSchema).length > 0;

  if (!hasParameters) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <CheckCircle className="h-12 w-12 text-success-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            No Configuration Required
          </h3>
          <p className="text-slate-600 dark:text-slate-400 mb-4">
            This model uses default settings and doesn't require parameter configuration.
          </p>
          {onSubmit && (
            <Button variant="medical" onClick={onSubmit}>
              Proceed to Analysis
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-medical-500" />
          <div className="flex-1">
            <CardTitle>Configure Analysis Parameters</CardTitle>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Model: {model.name} v{model.version}
            </p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Parameter Fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(parameterSchema).map(([key, schema]: [string, any]) => (
            <div key={key} className={schema.type === 'boolean' ? 'md:col-span-2' : ''}>
              <ParameterField
                name={key}
                schema={schema}
                value={parameters[key]}
                onChange={(value) => handleParameterChange(key, value)}
                error={errors[key]}
              />
            </div>
          ))}
        </div>

        {/* Validation Summary */}
        <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isValid ? (
                <>
                  <CheckCircle className="h-5 w-5 text-success-500" />
                  <span className="text-sm text-success-700 dark:text-success-400 font-medium">
                    All parameters are valid
                  </span>
                </>
              ) : (
                <>
                  <AlertCircle className="h-5 w-5 text-warning-500" />
                  <span className="text-sm text-warning-700 dark:text-warning-400 font-medium">
                    {Object.keys(errors).length} field(s) need attention
                  </span>
                </>
              )}
            </div>

            {onSubmit && (
              <Button variant="medical" onClick={onSubmit} disabled={!isValid}>
                Start Analysis
              </Button>
            )}
          </div>
        </div>

        {/* Model Info */}
        {model.description && (
          <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
            <p className="text-xs text-slate-600 dark:text-slate-400">
              <span className="font-semibold">About this model:</span> {model.description}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default ParameterConfigurator;
