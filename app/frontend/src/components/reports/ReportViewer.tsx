/**
 * Report Viewer
 *
 * Renders structured JSON report content as formatted cards.
 */

import React from 'react';

interface ReportContent {
  report_type?: string;
  generated_at?: string;
  model_info?: Record<string, string>;
  patient_info?: Record<string, string>;
  sections?: Array<{
    title: string;
    type: string;
    items?: any[];
    data?: Record<string, any>;
  }>;
  summary?: string;
  disclaimer?: string;
}

interface Props {
  content: ReportContent;
}

const InfoTable: React.FC<{ data: Record<string, any> }> = ({ data }) => (
  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
    {Object.entries(data).map(([key, value]) => (
      <React.Fragment key={key}>
        <span className="text-slate-500 dark:text-slate-400 capitalize">
          {key.replace(/_/g, ' ')}
        </span>
        <span className="text-slate-900 dark:text-slate-100">{String(value)}</span>
      </React.Fragment>
    ))}
  </div>
);

const ConfidenceBar: React.FC<{ value: number }> = ({ value }) => {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-medical-500 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-slate-600 dark:text-slate-400 w-10 text-right">
        {pct}%
      </span>
    </div>
  );
};

const ReportViewer: React.FC<Props> = ({ content }) => {
  return (
    <div className="space-y-4">
      {/* Patient Info */}
      {content.patient_info && (
        <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
          <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
            Patient Information
          </h4>
          <InfoTable data={content.patient_info} />
        </div>
      )}

      {/* Model Info */}
      {content.model_info && (
        <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
          <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
            Model Information
          </h4>
          <InfoTable data={content.model_info} />
        </div>
      )}

      {/* Sections */}
      {content.sections?.map((section, idx) => (
        <div
          key={idx}
          className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50"
        >
          <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
            {section.title}
          </h4>

          {section.type === 'findings' && section.items && (
            <ul className="space-y-2">
              {section.items.map((item, i) => (
                <li
                  key={i}
                  className="text-sm text-slate-800 dark:text-slate-200"
                >
                  <div className="flex justify-between items-start">
                    <span>
                      {typeof item === 'string'
                        ? item
                        : item.description || item.text || JSON.stringify(item)}
                    </span>
                  </div>
                  {typeof item === 'object' && item.confidence != null && (
                    <div className="mt-1 max-w-xs">
                      <ConfidenceBar value={item.confidence} />
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}

          {section.type === 'scores' && section.data && (
            <div className="space-y-2">
              {Object.entries(section.data).map(([key, value]) => (
                <div key={key}>
                  <div className="text-xs text-slate-500 dark:text-slate-400 capitalize mb-0.5">
                    {key.replace(/_/g, ' ')}
                  </div>
                  {typeof value === 'number' && value <= 1 ? (
                    <ConfidenceBar value={value} />
                  ) : (
                    <span className="text-sm text-slate-900 dark:text-slate-100">
                      {String(value)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {(section.type === 'measurements' ||
            section.type === 'technical' ||
            section.type === 'raw') &&
            section.data && <InfoTable data={section.data} />}
        </div>
      ))}

      {/* Summary */}
      {content.summary && (
        <div className="p-4 rounded-lg bg-medical-50 dark:bg-medical-950/20 border border-medical-200 dark:border-medical-800">
          <h4 className="text-sm font-semibold text-medical-700 dark:text-medical-300 mb-1">
            Summary
          </h4>
          <p className="text-sm text-slate-700 dark:text-slate-300">
            {content.summary}
          </p>
        </div>
      )}

      {/* Disclaimer */}
      {content.disclaimer && (
        <p className="text-xs text-slate-400 dark:text-slate-500 italic">
          {content.disclaimer}
        </p>
      )}
    </div>
  );
};

export default ReportViewer;
