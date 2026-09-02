/**
 * AcceptInvitationPage — public, no auth (the invitee has no account yet).
 *
 * The token in the URL is the whole credential, so the page shows only what
 * the backend's PublicInvitationSerializer returns: the clinic's name, the
 * invited address, and the expiry. Every invalid state — unknown, expired,
 * revoked, already used — comes back as the same 404 and is rendered as one
 * message, so the page can't be used to probe which addresses have accounts.
 *
 * The email is fixed by the invitation and shown read-only: letting the
 * invitee change it would turn a clinic invite into an open registration.
 */
import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { AlertCircle, Building2, Loader2, ShieldCheck } from 'lucide-react';

import { apiClient } from '../utils/api';
import type { PublicInvitation } from '../types/api';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';

const AcceptInvitationPage: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const { t, i18n } = useTranslation('common');
  const navigate = useNavigate();

  const [invitation, setInvitation] = useState<PublicInvitation | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ first_name: '', last_name: '', password: '', confirm: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    let cancelled = false;
    apiClient.getInvitation(token)
      .then((data) => !cancelled && setInvitation(data))
      .catch(() => !cancelled && setInvitation(null))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [token]);

  const set = (k: keyof typeof form, v: string) => {
    setForm((prev) => ({ ...prev, [k]: v }));
    setErrors((prev) => ({ ...prev, [k]: '' }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (form.password !== form.confirm) {
      setErrors({ confirm: t('management.accept.passwordMismatch') });
      return;
    }

    setSubmitting(true);
    try {
      await apiClient.acceptInvitation(token, {
        password: form.password,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
      });
      toast.success(t('management.accept.success'));
      navigate('/auth/login', { replace: true });
    } catch (err) {
      // Django's password validators return the useful text ("too short",
      // "too common"); surface it rather than a generic failure.
      const detail = (err as { data?: { password?: string[]; error?: string } })?.data;
      if (detail?.password?.length) {
        setErrors({ password: detail.password.join(' ') });
      } else if (detail?.error) {
        toast.error(detail.error);
      } else {
        toast.error(t('management.accept.error'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[60vh] text-slate-400">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (!invitation) {
    return (
      <div className="container mx-auto px-4 py-16 max-w-md text-center">
        <AlertCircle className="h-12 w-12 mx-auto text-amber-500 mb-4" />
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
          {t('management.accept.invalidTitle')}
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">
          {t('management.accept.invalidBody')}
        </p>
        <Link to="/auth/login">
          <Button variant="medical">{t('management.accept.goToLogin')}</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-12 max-w-md">
      <div className="medical-card p-6 sm:p-8">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center h-12 w-12 rounded-full bg-medical-100 dark:bg-medical-900/40 mb-4">
            <Building2 className="h-6 w-6 text-medical-600 dark:text-medical-400" />
          </div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
            {t('management.accept.title', { clinic: invitation.clinic_name })}
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
            {t('management.accept.subtitle')}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <span className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              {t('labels.email')}
            </span>
            <div className="px-3 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-sm text-slate-600 dark:text-slate-300 break-all">
              {invitation.email}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label={t('management.accept.firstName')}
              value={form.first_name}
              onChange={(e) => set('first_name', e.target.value)}
              disabled={submitting}
              autoComplete="given-name"
            />
            <Input
              label={t('management.accept.lastName')}
              value={form.last_name}
              onChange={(e) => set('last_name', e.target.value)}
              disabled={submitting}
              autoComplete="family-name"
            />
          </div>

          <Input
            label={t('management.accept.password')}
            type="password"
            required
            value={form.password}
            onChange={(e) => set('password', e.target.value)}
            error={errors.password}
            disabled={submitting}
            autoComplete="new-password"
          />
          <Input
            label={t('management.accept.confirmPassword')}
            type="password"
            required
            value={form.confirm}
            onChange={(e) => set('confirm', e.target.value)}
            error={errors.confirm}
            disabled={submitting}
            autoComplete="new-password"
          />

          <Button
            type="submit"
            variant="medical"
            className="w-full"
            loading={submitting}
            disabled={submitting || !form.password}
          >
            {t('management.accept.submit')}
          </Button>
        </form>

        <p className="flex items-start gap-2 text-xs text-slate-500 dark:text-slate-400 mt-6">
          <ShieldCheck className="h-4 w-4 shrink-0 mt-0.5" />
          <span>
            {t('management.accept.expiryNote', {
              date: new Date(invitation.expires_at).toLocaleDateString(i18n.language, {
                day: 'numeric', month: 'long', year: 'numeric',
              }),
            })}
          </span>
        </p>
      </div>
    </div>
  );
};

export default AcceptInvitationPage;
