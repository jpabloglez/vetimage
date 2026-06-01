/**
 * Template Selector
 *
 * Card-based selector for report templates in GenerateReportModal.
 */

import React, { useEffect, useState } from 'react';
import { FileText, Check } from 'lucide-react';
import { apiClient, type ReportTemplate } from '../../utils/api';

interface TemplateSelectorProps {
  selectedId: string | null;
  onSelect: (templateId: string | null) => void;
}

const TemplateSelector: React.FC<TemplateSelectorProps> = ({ selectedId, onSelect }) => {
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.getReportTemplates()
      .then(setTemplates)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-sm text-slate-500">Loading templates...</div>;
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
        Report Template (optional)
      </label>

      <div className="grid grid-cols-2 gap-3">
        {/* No template option */}
        <button
          onClick={() => onSelect(null)}
          className={`p-3 rounded-lg border-2 text-left transition-all ${
            selectedId === null
              ? 'border-medical-500 bg-medical-50 dark:bg-medical-950/20'
              : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
          }`}
        >
          <div className="flex items-center justify-between">
            <FileText className="w-4 h-4 text-slate-400" />
            {selectedId === null && <Check className="w-4 h-4 text-medical-500" />}
          </div>
          <div className="text-sm font-medium mt-1">Default</div>
          <div className="text-xs text-slate-500">Standard report format</div>
        </button>

        {templates.map(tpl => (
          <button
            key={tpl.id}
            onClick={() => onSelect(tpl.id)}
            className={`p-3 rounded-lg border-2 text-left transition-all ${
              selectedId === tpl.id
                ? 'border-medical-500 bg-medical-50 dark:bg-medical-950/20'
                : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <FileText className="w-4 h-4 text-medical-500" />
              {selectedId === tpl.id && <Check className="w-4 h-4 text-medical-500" />}
            </div>
            <div className="text-sm font-medium mt-1">{tpl.name}</div>
            <div className="text-xs text-slate-500">{tpl.template_type}</div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default TemplateSelector;
