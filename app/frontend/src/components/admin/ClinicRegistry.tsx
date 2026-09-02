/**
 * ClinicRegistry — every tenant on the platform, with usage counts.
 *
 * Registering a clinic does not create an account for the customer: it creates
 * the empty clinic and invites its first administrator, who sets a password
 * only they ever know. That keeps the rule that platform staff never write
 * into a clinic under someone else's identity.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Building2, Check, Copy, Loader2, Plus, X } from 'lucide-react';

import { apiClient } from '../../utils/api';
import type { AdminClinic } from '../../types/api';
import Card, { CardContent, CardHeader, CardTitle } from '../ui/Card';
import Button from '../ui/Button';
import Input from '../ui/Input';

type SortKey = 'name' | 'members' | 'patients_count' | 'studies_count' | 'analyses_count';

export const ClinicRegistry: React.FC = () => {
  const { t, i18n } = useTranslation('common');

  const [clinics, setClinics] = useState<AdminClinic[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: '', city: '', admin_email: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [invite, setInvite] = useState<{ email: string; path: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: 'name', desc: false });

  const load = useCallback(async () => {
    try {
      setClinics(await apiClient.getAdminClinics());
    } catch {
      toast.error(t('admin.clinics.loadError'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => { void load(); }, [load]);

  const sorted = useMemo(() => {
    const rows = [...clinics];
    rows.sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      const cmp = typeof av === 'string' && typeof bv === 'string'
        ? av.localeCompare(bv)
        : Number(av) - Number(bv);
      return sort.desc ? -cmp : cmp;
    });
    return rows;
  }, [clinics, sort]);

  const toggleSort = (key: SortKey) =>
    setSort((prev) => ({ key, desc: prev.key === key ? !prev.desc : true }));

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setSaving(true);
    try {
      const created = await apiClient.createAdminClinic({
        name: form.name.trim(),
        city: form.city.trim(),
        admin_email: form.admin_email.trim().toLowerCase(),
      });
      setInvite({ email: created.admin_email, path: created.invitation_path });
      setForm({ name: '', city: '', admin_email: '' });
      setShowForm(false);
      await load();
      toast.success(t('admin.clinics.registered'));
    } catch (err) {
      const data = (err as { data?: Record<string, string[]> })?.data ?? {};
      const next: Record<string, string> = {};
      for (const field of ['name', 'admin_email'] as const) {
        if (data[field]?.length) next[field] = data[field][0];
      }
      setErrors(next);
      if (!Object.keys(next).length) toast.error(t('admin.clinics.registerError'));
    } finally {
      setSaving(false);
    }
  };

  const copyInvite = async () => {
    if (!invite) return;
    const link = `${window.location.origin}${invite.path}`;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast.success(t('admin.clinics.linkCopied'));
    } catch {
      toast.error(link);
    }
  };

  const fmtDate = (iso: string | null) =>
    iso
      ? new Date(iso).toLocaleDateString(i18n.language, {
          day: 'numeric', month: 'short', year: 'numeric',
        })
      : '—';

  const columns: { key: SortKey; label: string; numeric?: boolean }[] = [
    { key: 'name', label: t('admin.clinics.name') },
    { key: 'members', label: t('admin.clinics.members'), numeric: true },
    { key: 'patients_count', label: t('admin.clinics.patients'), numeric: true },
    { key: 'studies_count', label: t('admin.clinics.studies'), numeric: true },
    { key: 'analyses_count', label: t('admin.clinics.analyses'), numeric: true },
  ];

  return (
    <Card variant="medical">
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <CardTitle>{t('admin.clinics.title')}</CardTitle>
        <Button
          variant={showForm ? 'outline' : 'medical'}
          onClick={() => setShowForm((v) => !v)}
        >
          {showForm ? <X className="h-4 w-4 mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
          {showForm ? t('buttons.cancel') : t('admin.clinics.register')}
        </Button>
      </CardHeader>
      <CardContent className="space-y-6">
        {showForm && (
          <form
            onSubmit={handleRegister}
            className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 space-y-4"
          >
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {t('admin.clinics.registerHint')}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Input
                label={t('admin.clinics.name')}
                required
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                error={errors.name}
                disabled={saving}
              />
              <Input
                label={t('admin.clinics.city')}
                value={form.city}
                onChange={(e) => setForm((p) => ({ ...p, city: e.target.value }))}
                disabled={saving}
              />
              <Input
                label={t('admin.clinics.adminEmail')}
                type="email"
                required
                value={form.admin_email}
                onChange={(e) => setForm((p) => ({ ...p, admin_email: e.target.value }))}
                error={errors.admin_email}
                disabled={saving}
              />
            </div>
            <Button
              type="submit"
              variant="medical"
              loading={saving}
              disabled={saving || !form.name.trim() || !form.admin_email.trim()}
            >
              {t('admin.clinics.register')}
            </Button>
          </form>
        )}

        {invite && (
          <div className="p-4 rounded-lg border border-medical-200 dark:border-medical-800 bg-medical-50 dark:bg-medical-900/20">
            <p className="text-sm text-slate-700 dark:text-slate-300 mb-3">
              {t('admin.clinics.inviteSent', { email: invite.email })}
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs bg-white dark:bg-slate-900 px-3 py-2 rounded border border-slate-200 dark:border-slate-700 overflow-x-auto whitespace-nowrap">
                {window.location.origin}{invite.path}
              </code>
              <Button variant="outline" onClick={copyInvite}>
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              </Button>
              <button
                type="button"
                onClick={() => setInvite(null)}
                aria-label={t('buttons.close')}
                className="p-2 text-slate-400 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-10 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : sorted.length === 0 ? (
          <div className="text-center py-10 text-sm text-slate-500 dark:text-slate-400">
            <Building2 className="h-8 w-8 mx-auto mb-2 opacity-40" />
            {t('admin.clinics.empty')}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                  {columns.map((col) => (
                    <th
                      key={col.key}
                      className={`py-2 pr-4 font-medium ${col.numeric ? 'text-right' : ''}`}
                    >
                      <button
                        type="button"
                        onClick={() => toggleSort(col.key)}
                        className="uppercase tracking-wide hover:text-medical-600"
                      >
                        {col.label}
                        {sort.key === col.key && (sort.desc ? ' ↓' : ' ↑')}
                      </button>
                    </th>
                  ))}
                  <th className="py-2 pr-4 font-medium">{t('admin.clinics.founder')}</th>
                  <th className="py-2 font-medium">{t('admin.clinics.lastActivity')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {sorted.map((c) => (
                  <tr key={c.id}>
                    <td className="py-3 pr-4">
                      <div className="font-medium text-slate-900 dark:text-slate-100">{c.name}</div>
                      {c.city && <div className="text-xs text-slate-500">{c.city}</div>}
                    </td>
                    <td className="py-3 pr-4 text-right tabular-nums">{c.members}</td>
                    <td className="py-3 pr-4 text-right tabular-nums">{c.patients_count}</td>
                    <td className="py-3 pr-4 text-right tabular-nums">{c.studies_count}</td>
                    <td className="py-3 pr-4 text-right tabular-nums">{c.analyses_count}</td>
                    <td className="py-3 pr-4 text-slate-500 break-all">{c.founder_email ?? '—'}</td>
                    <td className="py-3 text-slate-500 whitespace-nowrap tabular-nums">
                      {fmtDate(c.last_activity)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default ClinicRegistry;
