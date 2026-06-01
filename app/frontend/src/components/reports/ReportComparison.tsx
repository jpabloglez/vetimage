/**
 * Report Comparison
 *
 * Side-by-side view of two reports with diff highlighting on findings.
 */

import React, { useMemo } from 'react';
import type { Report } from '../../utils/api';
import { computeDiff, type DiffSegment } from '../../hooks/useDiff';

interface ReportComparisonProps {
  reportA: Report;
  reportB: Report;
}

function extractFindings(report: Report): string {
  const sections = report.content?.sections || [];
  const findings = sections.find((s: any) => s.type === 'findings');
  if (!findings) return '';

  const items = findings.items || [];
  return items
    .map((item: any) =>
      typeof item === 'string' ? item : item.description || item.text || JSON.stringify(item)
    )
    .join('\n');
}

function renderDiff(segments: DiffSegment[]) {
  return segments.map((seg, i) => {
    if (seg.type === 'same') {
      return <span key={i}>{seg.text}</span>;
    }
    if (seg.type === 'added') {
      return (
        <span key={i} className="bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300">
          {seg.text}
        </span>
      );
    }
    return (
      <span key={i} className="bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 line-through">
        {seg.text}
      </span>
    );
  });
}

function renderSection(section: any) {
  if (section.type === 'findings') {
    const items = section.items || [];
    return (
      <ul className="list-disc pl-5 space-y-1">
        {items.map((item: any, i: number) => (
          <li key={i} className="text-sm">
            {typeof item === 'string' ? item : item.description || JSON.stringify(item)}
          </li>
        ))}
      </ul>
    );
  }
  if (section.type === 'scores' || section.type === 'measurements' || section.type === 'technical') {
    const data = section.data || {};
    return (
      <div className="space-y-1">
        {Object.entries(data).map(([key, value]) => (
          <div key={key} className="flex justify-between text-sm">
            <span className="text-slate-600 dark:text-slate-400">{key.replace(/_/g, ' ')}</span>
            <span className="font-medium">{String(value)}</span>
          </div>
        ))}
      </div>
    );
  }
  return <pre className="text-xs">{JSON.stringify(section.data || section.items, null, 2)}</pre>;
}

const ReportComparison: React.FC<ReportComparisonProps> = ({ reportA, reportB }) => {
  const findingsA = useMemo(() => extractFindings(reportA), [reportA]);
  const findingsB = useMemo(() => extractFindings(reportB), [reportB]);
  const diffSegments = useMemo(() => computeDiff(findingsA, findingsB), [findingsA, findingsB]);

  const sectionsA = reportA.content?.sections || [];
  const sectionsB = reportB.content?.sections || [];

  return (
    <div className="space-y-6">
      {/* Diff Highlight */}
      {findingsA && findingsB && (
        <div className="medical-card p-4">
          <h4 className="text-sm font-semibold mb-2 text-slate-700 dark:text-slate-300">
            Findings Diff
          </h4>
          <p className="text-sm leading-relaxed">
            {renderDiff(diffSegments)}
          </p>
        </div>
      )}

      {/* Side-by-side Sections */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Report A */}
        <div className="medical-card p-4 space-y-4">
          <h3 className="text-sm font-bold text-medical-600 truncate">{reportA.title}</h3>
          {sectionsA.map((section: any, i: number) => (
            <div key={i}>
              <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1">
                {section.title}
              </h4>
              {renderSection(section)}
            </div>
          ))}
        </div>

        {/* Report B */}
        <div className="medical-card p-4 space-y-4">
          <h3 className="text-sm font-bold text-medical-600 truncate">{reportB.title}</h3>
          {sectionsB.map((section: any, i: number) => (
            <div key={i}>
              <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1">
                {section.title}
              </h4>
              {renderSection(section)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ReportComparison;
