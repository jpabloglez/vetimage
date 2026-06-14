/**
 * AiDisclaimer — a persistent, non-dismissable notice that AI output is
 * clinical decision support requiring veterinarian review, never a diagnosis.
 *
 * Render this anywhere AI results are presented (Analyze, Reports, owner views)
 * to keep VetImage firmly in the human-in-the-loop / decision-support posture
 * required by ACVR/ECVDI guidance.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';

interface AiDisclaimerProps {
  className?: string;
}

const AiDisclaimer: React.FC<AiDisclaimerProps> = ({ className = '' }) => {
  const { t } = useTranslation('common');
  return (
    <div
      role="note"
      className={`flex items-start gap-2.5 rounded-medical border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/20 px-3 py-2 text-sm text-amber-800 dark:text-amber-200 ${className}`}
    >
      <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-600 dark:text-amber-400" />
      <span>{t('aiDisclaimer.short')}</span>
    </div>
  );
};

export default AiDisclaimer;
