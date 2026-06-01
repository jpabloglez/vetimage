/**
 * Audit Report Preview
 *
 * Renders the structured JSON audit report.
 */

import React from 'react';
import { Shield, AlertTriangle, BarChart3 } from 'lucide-react';

interface AuditReportPreviewProps {
  content: Record<string, any>;
}

const AuditReportPreview: React.FC<AuditReportPreviewProps> = ({ content }) => {
  const sections = content.sections || [];

  return (
    <div className="space-y-6">
      {/* Report Header */}
      <div className="medical-card p-6">
        <div className="flex items-center gap-3 mb-2">
          <Shield className="w-6 h-6 text-medical-600" />
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
            {content.report_type || 'Audit Report'}
          </h2>
        </div>
        <p className="text-sm text-slate-500">
          Generated: {content.generated_at ? new Date(content.generated_at).toLocaleString() : 'N/A'}
        </p>
      </div>

      {/* Sections */}
      {sections.map((section: any, i: number) => (
        <div key={i} className="medical-card p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            {section.type === 'findings' && <AlertTriangle className="w-5 h-5 text-amber-500" />}
            {section.type === 'scores' && <BarChart3 className="w-5 h-5 text-medical-600" />}
            {section.title}
          </h3>

          {section.type === 'scores' && section.data && (
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              {Object.entries(section.data).map(([key, value]) => (
                <div key={key} className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-medical-600">{String(value)}</div>
                  <div className="text-sm text-slate-500 mt-1">{key.replace(/_/g, ' ')}</div>
                </div>
              ))}
            </div>
          )}

          {section.type === 'measurements' && section.data && (
            <div className="space-y-2">
              {Object.entries(section.data).map(([key, value]) => (
                <div key={key} className="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-700">
                  <span className="text-sm text-slate-600 dark:text-slate-400">
                    {key.replace(/_/g, ' ')}
                  </span>
                  <span className="text-sm font-semibold">{String(value)}</span>
                </div>
              ))}
            </div>
          )}

          {section.type === 'findings' && section.items && (
            <ul className="space-y-2">
              {section.items.map((item: any, j: number) => (
                <li key={j} className="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/10 rounded-lg">
                  <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                  <span className="text-sm">
                    {typeof item === 'string' ? item : item.description}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}

      {/* Summary */}
      {content.summary && (
        <div className="medical-card p-6">
          <h3 className="text-lg font-semibold mb-2">Summary</h3>
          <p className="text-sm text-slate-600 dark:text-slate-400">{content.summary}</p>
        </div>
      )}

      {/* Disclaimer */}
      {content.disclaimer && (
        <p className="text-xs text-slate-400 italic">{content.disclaimer}</p>
      )}
    </div>
  );
};

export default AuditReportPreview;
