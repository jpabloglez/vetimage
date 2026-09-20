/**
 * PlanUsageSection — what the clinic is using, against what its plan allows.
 *
 * Shown to every member, not just admins: a vet who hits the monthly quota
 * should be able to see why without having to ask someone.
 *
 * This reports; it never gates. The limits are applied by the backend at the
 * point work is created, so a bar approaching full is information, not a lock.
 * Anything this component decided would be advice a client could skip.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Users, Sparkles, HardDrive } from 'lucide-react';

import { apiClient } from '../../utils/api';
import type { ClinicUsage, PlanAllowance } from '../../types/api';
import Card, { CardContent, CardHeader, CardTitle } from '../ui/Card';

/** Bytes in the units a vet reads, not a sysadmin. */
const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value < 10 ? value.toFixed(1) : Math.round(value)} ${units[i]}`;
};

interface MeterProps {
  icon: React.ElementType;
  label: string;
  allowance: PlanAllowance;
  format?: (n: number) => string;
  unlimitedLabel: string;
}

const Meter: React.FC<MeterProps> = ({
  icon: Icon, label, allowance, format = (n) => String(n), unlimitedLabel,
}) => {
  const { used, limit, exceeded } = allowance;
  const unlimited = limit === null;
  const pct = unlimited ? 0 : Math.min(100, Math.round((used / Math.max(limit, 1)) * 100));

  // Amber before the wall, not only at it — the point is to be seen coming.
  const tone = exceeded
    ? 'bg-red-500'
    : pct >= 80
      ? 'bg-amber-500'
      : 'bg-medical-500';

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
          <Icon className="h-4 w-4" />
          {label}
        </div>
        <div className="text-sm tabular-nums text-slate-900 dark:text-slate-100">
          {format(used)}
          <span className="text-slate-400">
            {unlimited ? ` / ${unlimitedLabel}` : ` / ${format(limit)}`}
          </span>
        </div>
      </div>
      {!unlimited && (
        <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
          <div
            className={`h-full rounded-full ${tone}`}
            style={{ width: `${Math.max(pct, 2)}%` }}
          />
        </div>
      )}
    </div>
  );
};

export const PlanUsageSection: React.FC = () => {
  const { t } = useTranslation('common');
  const [usage, setUsage] = useState<ClinicUsage | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    apiClient.getClinicUsage()
      .then((u) => { if (!cancelled) setUsage(u); })
      .catch(() => { /* a missing plan is not an error worth a toast */ })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <Card variant="medical">
        <CardContent>
          <div className="flex justify-center py-8 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!usage) return null;

  return (
    <Card variant="medical">
      <CardHeader>
        <CardTitle>
          {t('management.plan.title')}
          {usage.plan && (
            <span className="ml-2 text-sm font-normal text-slate-500 dark:text-slate-400">
              {usage.plan.name}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <p className="text-sm text-slate-600 dark:text-slate-400">
          {t('management.plan.description')}
        </p>

        <div className="space-y-1">
          <Meter
            icon={Users}
            label={t('management.plan.seats')}
            allowance={usage.seats}
            unlimitedLabel={t('management.plan.unlimited')}
          />
          {/* Without this the count looks wrong: an admin sees 2 of 2 with one
              person on the roster and no way to account for the other. */}
          {usage.seats.pending_invitations > 0 && (
            <p className="text-xs text-slate-500 dark:text-slate-400 pl-6">
              {t('management.plan.seatsBreakdown', {
                members: usage.seats.members,
                pending: usage.seats.pending_invitations,
              })}
            </p>
          )}
        </div>
        <Meter
          icon={Sparkles}
          label={t('management.plan.analyses')}
          allowance={usage.analyses}
          unlimitedLabel={t('management.plan.unlimited')}
        />
        <Meter
          icon={HardDrive}
          label={t('management.plan.storage')}
          allowance={usage.storage}
          format={formatBytes}
          unlimitedLabel={t('management.plan.unlimited')}
        />

        {/* Says plainly what a full meter does and does not mean. Someone
            reading a red bar needs to know their records are not at risk. */}
        {(usage.seats.exceeded || usage.analyses.exceeded || usage.storage.exceeded) && (
          <p className="text-sm rounded-lg px-3 py-2 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300">
            {t('management.plan.atLimit')}
          </p>
        )}
      </CardContent>
    </Card>
  );
};

export default PlanUsageSection;
