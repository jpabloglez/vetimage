/**
 * ClinicProfileSection — the clinic's own details.
 *
 * A clinic provisioned automatically is named after the email local part
 * ('jsmith'), which is nobody's clinic name and, until now, could not be
 * changed from anywhere in the app. The name is what colleagues see on an
 * invitation and what owners see on a shared report, so it is worth fixing.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Loader2 } from 'lucide-react';

import { apiClient } from '../../utils/api';
import { useAuth } from '../../contexts';
import Card, { CardContent, CardHeader, CardTitle } from '../ui/Card';
import Button from '../ui/Button';
import Input from '../ui/Input';

interface Form {
  name: string;
  address: string;
  city: string;
  billing_address: string;
  billing_code: string;
}

const EMPTY: Form = {
  name: '', address: '', city: '', billing_address: '', billing_code: '',
};

export const ClinicProfileSection: React.FC = () => {
  const { t } = useTranslation('common');
  const { refreshUser } = useAuth();

  const [form, setForm] = useState<Form>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;
    apiClient.getClinicProfile()
      .then((c) => {
        if (cancelled) return;
        setForm({
          name: c.name ?? '',
          address: c.address ?? '',
          city: c.city ?? '',
          billing_address: c.billing_address ?? '',
          billing_code: c.billing_code ?? '',
        });
      })
      .catch(() => !cancelled && toast.error(t('management.clinic.loadError')))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const set = (k: keyof Form, v: string) => {
    setForm((prev) => ({ ...prev, [k]: v }));
    setErrors((prev) => ({ ...prev, [k]: '' }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setSaving(true);
    try {
      await apiClient.updateClinicProfile(form);
      // The clinic name is shown in the navbar and page subtitles.
      await refreshUser();
      toast.success(t('management.clinic.saved'));
    } catch (err) {
      const data = (err as { data?: Record<string, string[]> })?.data ?? {};
      if (data.name?.length) setErrors({ name: data.name[0] });
      else toast.error(t('management.clinic.saveError'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card variant="medical">
      <CardHeader>
        <CardTitle>{t('management.clinic.title')}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex justify-center py-10 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {t('management.clinic.description')}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-5">
              <Input
                label={t('management.clinic.name')}
                required
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
                error={errors.name}
                disabled={saving}
              />
              <Input
                label={t('management.clinic.city')}
                value={form.city}
                onChange={(e) => set('city', e.target.value)}
                disabled={saving}
              />
              <Input
                label={t('management.clinic.address')}
                value={form.address}
                onChange={(e) => set('address', e.target.value)}
                disabled={saving}
              />
              <Input
                label={t('management.clinic.billingCode')}
                value={form.billing_code}
                onChange={(e) => set('billing_code', e.target.value)}
                disabled={saving}
              />
            </div>
            <Button
              type="submit"
              variant="medical"
              loading={saving}
              disabled={saving || !form.name.trim()}
            >
              {t('buttons.saveChanges')}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
};

export default ClinicProfileSection;
