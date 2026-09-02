/**
 * MembersSection — the clinic's staff roster and the operations on it.
 *
 * Revoking access is the consequential one, so the UI is explicit about what
 * it does and does not do: the person can no longer sign in, and the records
 * they authored stay with the clinic. It is reversible, and revoked members
 * remain listed so an admin can see and undo it — a removal that vanishes from
 * the screen is one nobody can audit.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Loader2, RotateCcw, ShieldCheck, UserMinus, Users } from 'lucide-react';

import { apiClient } from '../../utils/api';
import type { ClinicMember } from '../../types/api';
import { useAuth } from '../../contexts';
import Card, { CardContent, CardHeader, CardTitle } from '../ui/Card';
import ConfirmDialog from '../ui/ConfirmDialog';

/** Mirrors ASSIGNABLE_ROLES in users/serializers_clinic.py. */
const ASSIGNABLE_ROLES: { value: number; key: string }[] = [
  { value: 1, key: 'roles.user' },
  { value: 4, key: 'roles.manager' },
  { value: 3, key: 'roles.admin' },
];

export const MembersSection: React.FC = () => {
  const { t, i18n } = useTranslation('common');
  const { user } = useAuth();

  const [members, setMembers] = useState<ClinicMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [revoking, setRevoking] = useState<ClinicMember | null>(null);

  const load = useCallback(async () => {
    try {
      setMembers(await apiClient.getClinicMembers());
    } catch {
      toast.error(t('management.members.loadError'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => { void load(); }, [load]);

  /** The backend's message is the useful one — it explains *why* (last admin,
   *  own account), which a generic failure would throw away. */
  const failWith = (err: unknown, fallbackKey: string) => {
    const detail = (err as { data?: { error?: string } })?.data?.error;
    toast.error(detail || t(fallbackKey));
  };

  const changeRole = async (member: ClinicMember, role: number) => {
    setBusy(member.user_id);
    try {
      await apiClient.setClinicMemberRole(member.user_id, role);
      await load();
      toast.success(t('management.members.roleChanged'));
    } catch (err) {
      failWith(err, 'management.members.roleError');
    } finally {
      setBusy(null);
    }
  };

  const doRevoke = async () => {
    if (!revoking) return;
    setBusy(revoking.user_id);
    try {
      await apiClient.revokeClinicMember(revoking.user_id);
      await load();
      toast.success(t('management.members.revoked'));
    } catch (err) {
      failWith(err, 'management.members.revokeError');
    } finally {
      setBusy(null);
      setRevoking(null);
    }
  };

  const restore = async (member: ClinicMember) => {
    setBusy(member.user_id);
    try {
      await apiClient.restoreClinicMember(member.user_id);
      await load();
      toast.success(t('management.members.restored'));
    } catch (err) {
      failWith(err, 'management.members.restoreError');
    } finally {
      setBusy(null);
    }
  };

  /** Falls back to the email when someone has not filled in their name. */
  const displayName = (m: ClinicMember) => {
    const name = [m.first_name, m.last_name].filter(Boolean).join(' ').trim();
    return name || m.email;
  };

  const hasRealName = (m: ClinicMember) =>
    Boolean([m.first_name, m.last_name].filter(Boolean).join('').trim());

  const fmtLogin = (iso: string | null) =>
    iso
      ? new Date(iso).toLocaleDateString(i18n.language, {
          day: 'numeric', month: 'short', year: 'numeric',
        })
      : '—';

  const selectCls =
    'px-2 py-1 rounded-md border border-slate-300 dark:border-slate-600 ' +
    'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm ' +
    'focus:outline-none focus:ring-2 focus:ring-medical-500 disabled:opacity-50';

  return (
    <>
      <Card variant="medical">
        <CardHeader>
          <CardTitle>{t('management.members.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-5">
            {t('management.members.description')}
          </p>

          {loading ? (
            <div className="flex justify-center py-10 text-slate-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : members.length === 0 ? (
            <div className="text-center py-10 text-sm text-slate-500 dark:text-slate-400">
              <Users className="h-8 w-8 mx-auto mb-2 opacity-40" />
              {t('management.members.empty')}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                    <th className="py-2 pr-4 font-medium">{t('management.members.person')}</th>
                    <th className="py-2 pr-4 font-medium">{t('management.members.role')}</th>
                    <th className="py-2 pr-4 font-medium">{t('management.members.lastSignIn')}</th>
                    <th className="py-2 font-medium sr-only">{t('management.members.actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {members.map((m) => {
                    const isSelf = m.user_id === user?.id;
                    const working = busy === m.user_id;
                    return (
                      <tr key={m.user_id} className={m.is_active ? '' : 'opacity-60'}>
                        <td className="py-3 pr-4">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-slate-900 dark:text-slate-100">
                              {displayName(m)}
                            </span>
                            {m.is_clinic_admin && (
                              <ShieldCheck
                                className="h-3.5 w-3.5 text-medical-500"
                                aria-label={t('roles.admin')}
                              />
                            )}
                            {isSelf && (
                              <span className="text-xs text-slate-400">
                                {t('management.members.you')}
                              </span>
                            )}
                            {!m.is_active && (
                              <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">
                                {t('management.members.revokedBadge')}
                              </span>
                            )}
                          </div>
                          {/* Only when it is not already the display name. */}
                          {hasRealName(m) && (
                            <div className="text-xs text-slate-500 break-all">{m.email}</div>
                          )}
                          {(m.job_title || m.department) && (
                            <div className="text-xs text-slate-400">
                              {[m.job_title, m.department].filter(Boolean).join(' · ')}
                            </div>
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          <select
                            className={selectCls}
                            value={m.role}
                            disabled={working || !m.is_active}
                            aria-label={t('management.members.roleFor', { name: displayName(m) })}
                            onChange={(e) => changeRole(m, Number(e.target.value))}
                          >
                            {ASSIGNABLE_ROLES.map((r) => (
                              <option key={r.value} value={r.value}>{t(r.key)}</option>
                            ))}
                          </select>
                        </td>
                        <td className="py-3 pr-4 text-slate-500 whitespace-nowrap tabular-nums">
                          {fmtLogin(m.last_login)}
                        </td>
                        <td className="py-3 text-right whitespace-nowrap">
                          {working ? (
                            <Loader2 className="h-4 w-4 animate-spin inline text-slate-400" />
                          ) : m.is_active ? (
                            !isSelf && (
                              <button
                                type="button"
                                onClick={() => setRevoking(m)}
                                aria-label={t('management.members.revokeFor', { name: displayName(m) })}
                                title={t('management.members.revoke')}
                                className="p-1.5 rounded-md text-slate-500 hover:text-red-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                              >
                                <UserMinus className="h-4 w-4" />
                              </button>
                            )
                          ) : (
                            <button
                              type="button"
                              onClick={() => restore(m)}
                              aria-label={t('management.members.restoreFor', { name: displayName(m) })}
                              title={t('management.members.restore')}
                              className="p-1.5 rounded-md text-slate-500 hover:text-medical-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                            >
                              <RotateCcw className="h-4 w-4" />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={revoking !== null}
        onCancel={() => setRevoking(null)}
        onConfirm={doRevoke}
        title={t('management.members.revokeTitle')}
        message={t('management.members.revokeConfirm', {
          name: revoking ? displayName(revoking) : '',
        })}
        confirmLabel={t('management.members.revoke')}
        danger
      />
    </>
  );
};

export default MembersSection;
