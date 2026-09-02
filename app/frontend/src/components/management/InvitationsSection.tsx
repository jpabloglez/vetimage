/**
 * InvitationsSection — Clinic Admins only.
 *
 * Accepting an invitation grants immediate access to every patient, study and
 * report in the clinic, so this is a privilege grant, not a contact form. Two
 * things follow from that in the UI: the roster of pending invitations is
 * always visible (an unnoticed pending invite is an open door), and revoking
 * is one click away and asks first.
 *
 * The backend emails the link. In development EMAIL_BACKEND is the console
 * backend, so nothing is delivered — hence Copy link, which is also the
 * fallback whenever mail is misconfigured in production.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Check, Copy, Loader2, Mail, UserPlus, X } from 'lucide-react';

import { apiClient } from '../../utils/api';
import type { ClinicInvitation } from '../../types/api';
import Card, { CardContent, CardHeader, CardTitle } from '../ui/Card';
import Button from '../ui/Button';
import Input from '../ui/Input';
import ConfirmDialog from '../ui/ConfirmDialog';

/** Mirrors INVITABLE_ROLES in users/serializers_invitations.py. */
const INVITABLE_ROLES: { value: number; key: string }[] = [
  { value: 1, key: 'roles.user' },
  { value: 4, key: 'roles.manager' },
  { value: 3, key: 'roles.admin' },
];

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  accepted: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  revoked: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
  expired: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
};

export const InvitationsSection: React.FC = () => {
  const { t, i18n } = useTranslation('common');

  const [invitations, setInvitations] = useState<ClinicInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState(1);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [revoking, setRevoking] = useState<ClinicInvitation | null>(null);

  const load = useCallback(async () => {
    try {
      setInvitations(await apiClient.getClinicInvitations());
    } catch {
      toast.error(t('management.invitations.loadError'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => { void load(); }, [load]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldError(null);
    setAdding(true);
    try {
      await apiClient.createClinicInvitation(email.trim().toLowerCase(), role);
      setEmail('');
      setRole(1);
      await load();
      toast.success(t('management.invitations.sent'));
    } catch (err) {
      // The backend's messages are the useful ones here ("already in this
      // clinic", "already pending") — show them rather than a generic failure.
      const detail =
        (err as { data?: { email?: string[]; role?: string[] } })?.data?.email?.[0] ??
        (err as { data?: { role?: string[] } })?.data?.role?.[0] ??
        null;
      setFieldError(detail);
      if (!detail) toast.error(t('management.invitations.sendError'));
    } finally {
      setAdding(false);
    }
  };

  const handleCopy = async (invitation: ClinicInvitation) => {
    const link = `${window.location.origin}${invitation.accept_path}`;
    try {
      await navigator.clipboard.writeText(link);
      setCopiedId(invitation.id);
      setTimeout(() => setCopiedId(null), 2000);
      toast.success(t('management.invitations.copied'));
    } catch {
      // Clipboard is blocked outside a secure context; show the link so the
      // admin can still select it by hand rather than hitting a dead end.
      toast.error(link);
    }
  };

  const handleRevoke = async () => {
    if (!revoking) return;
    try {
      await apiClient.revokeClinicInvitation(revoking.id);
      await load();
      toast.success(t('management.invitations.revoked'));
    } catch {
      toast.error(t('management.invitations.revokeError'));
    } finally {
      setRevoking(null);
    }
  };

  const fmt = (iso: string) =>
    new Date(iso).toLocaleDateString(i18n.language, {
      day: 'numeric', month: 'short', year: 'numeric',
    });

  const roleLabel = (value: number) =>
    t(INVITABLE_ROLES.find((r) => r.value === value)?.key ?? 'roles.user');

  const selectCls =
    'w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 ' +
    'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm ' +
    'focus:outline-none focus:ring-2 focus:ring-medical-500';

  return (
    <>
      <Card variant="medical">
        <CardHeader>
          <CardTitle>{t('management.invitations.title')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {t('management.invitations.description')}
          </p>

          <form
            onSubmit={handleInvite}
            className="grid grid-cols-1 sm:grid-cols-[1fr_auto_auto] gap-3 sm:items-end"
          >
            <Input
              label={t('management.invitations.email')}
              type="email"
              required
              value={email}
              onChange={(e) => { setEmail(e.target.value); setFieldError(null); }}
              disabled={adding}
              error={fieldError ?? undefined}
              placeholder="colleague@clinic.example"
            />
            <div className="space-y-2">
              <label
                htmlFor="invite-role"
                className="block text-sm font-medium text-slate-700 dark:text-slate-300"
              >
                {t('management.invitations.role')}
              </label>
              <select
                id="invite-role"
                className={selectCls}
                value={role}
                onChange={(e) => setRole(Number(e.target.value))}
                disabled={adding}
              >
                {INVITABLE_ROLES.map((r) => (
                  <option key={r.value} value={r.value}>{t(r.key)}</option>
                ))}
              </select>
            </div>
            <Button
              type="submit"
              variant="medical"
              loading={adding}
              disabled={adding || !email.trim()}
              className="sm:mb-0"
            >
              <UserPlus className="h-4 w-4 mr-2" />
              {t('management.invitations.invite')}
            </Button>
          </form>

          {loading ? (
            <div className="flex justify-center py-8 text-slate-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : invitations.length === 0 ? (
            <div className="text-center py-8 text-sm text-slate-500 dark:text-slate-400">
              <Mail className="h-8 w-8 mx-auto mb-2 opacity-40" />
              {t('management.invitations.empty')}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                    <th className="py-2 pr-4 font-medium">{t('management.invitations.email')}</th>
                    <th className="py-2 pr-4 font-medium">{t('management.invitations.role')}</th>
                    <th className="py-2 pr-4 font-medium">{t('management.invitations.status')}</th>
                    <th className="py-2 pr-4 font-medium">{t('management.invitations.expires')}</th>
                    <th className="py-2 font-medium sr-only">{t('management.invitations.actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {invitations.map((inv) => (
                    <tr key={inv.id}>
                      <td className="py-3 pr-4 break-all">{inv.email}</td>
                      <td className="py-3 pr-4 whitespace-nowrap">{roleLabel(inv.role)}</td>
                      <td className="py-3 pr-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${
                            STATUS_STYLES[inv.status] ?? STATUS_STYLES.expired
                          }`}
                        >
                          {t(`management.invitations.statuses.${inv.status}`)}
                        </span>
                      </td>
                      <td className="py-3 pr-4 whitespace-nowrap text-slate-500 dark:text-slate-400 tabular-nums">
                        {fmt(inv.expires_at)}
                      </td>
                      <td className="py-3 text-right whitespace-nowrap">
                        {inv.status === 'pending' && (
                          <div className="inline-flex gap-1">
                            <button
                              type="button"
                              onClick={() => handleCopy(inv)}
                              title={t('management.invitations.copyLink')}
                              aria-label={t('management.invitations.copyLinkFor', { email: inv.email })}
                              className="p-1.5 rounded-md text-slate-500 hover:text-medical-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                            >
                              {copiedId === inv.id
                                ? <Check className="h-4 w-4 text-emerald-500" />
                                : <Copy className="h-4 w-4" />}
                            </button>
                            <button
                              type="button"
                              onClick={() => setRevoking(inv)}
                              title={t('management.invitations.revoke')}
                              aria-label={t('management.invitations.revokeFor', { email: inv.email })}
                              className="p-1.5 rounded-md text-slate-500 hover:text-red-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={revoking !== null}
        onCancel={() => setRevoking(null)}
        onConfirm={handleRevoke}
        title={t('management.invitations.revokeTitle')}
        message={t('management.invitations.revokeConfirm', { email: revoking?.email ?? '' })}
        confirmLabel={t('management.invitations.revoke')}
        danger
      />
    </>
  );
};

export default InvitationsSection;
