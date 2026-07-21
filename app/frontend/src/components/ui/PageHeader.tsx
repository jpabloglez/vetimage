import React from 'react';

interface PageHeaderProps {
  /** Lucide (or compatible) icon rendered at 8×8 in the medical accent colour. */
  icon: React.ElementType;
  title: string;
  subtitle?: string;
  /** Optional right-aligned actions (buttons, exports, …). */
  actions?: React.ReactNode;
  className?: string;
}

/**
 * Shared page header used across the main app views (Dashboard, Patients,
 * Analysis, Statistics, Tools, Monitor) so titles, icons and spacing stay
 * visually consistent. Pair with the standard page container
 * (`container mx-auto px-4 py-8 max-w-7xl`).
 */
const PageHeader: React.FC<PageHeaderProps> = ({
  icon: Icon,
  title,
  subtitle,
  actions,
  className,
}) => (
  <div className={`mb-8 ${className ?? ''}`}>
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="flex items-center gap-3 mb-2">
          <Icon className="w-8 h-8 text-medical-500 shrink-0" />
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">{title}</h1>
        </div>
        {subtitle && <p className="text-slate-600 dark:text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  </div>
);

export default PageHeader;
