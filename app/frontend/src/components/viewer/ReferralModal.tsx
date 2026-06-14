/**
 * ReferralModal — create and manage token-gated referral packages for a study.
 *
 * A referral package bundles the DICOM study + its report + a short history
 * summary into an unguessable link a specialist can open without a login
 * (rendered by ReferralPackagePage at /referral/:token). The study must already
 * be linked to a patient, since the bundle is animal-centric.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Copy, Trash2, Send } from 'lucide-react';
import { apiClient, type Study, type ReferralPackage, type ReferralUrgency } from '../../utils/api';
import { Button, Input, Modal, ModalContent, ModalFooter } from '../ui';

interface ReferralModalProps {
  study: Study | null;
  onClose: () => void;
}

type ExpiryOption = '7' | '30' | 'never';

const URGENCIES: ReferralUrgency[] = ['routine', 'urgent', 'emergency'];

const ReferralModal: React.FC<ReferralModalProps> = ({ study, onClose }) => {
  const { t } = useTranslation('viewer');
  const [packages, setPackages] = useState<ReferralPackage[]>([]);
  const [reason, setReason] = useState('');
  const [historySummary, setHistorySummary] = useState('');
  const [urgency, setUrgency] = useState<ReferralUrgency>('routine');
  const [expiry, setExpiry] = useState<ExpiryOption>('30');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [creating, setCreating] = useState(false);

  const animalId = study?.AnimalPatientID ?? null;

  const load = useCallback(() => {
    if (!animalId) { setPackages([]); return; }
    apiClient.getReferralPackages(animalId).then(setPackages).catch(() => setPackages([]));
  }, [animalId]);

  useEffect(() => { load(); }, [load]);

  const computeExpiry = (): string | null => {
    if (expiry === 'never') return null;
    const days = expiry === '7' ? 7 : 30;
    const d = new Date();
    d.setDate(d.getDate() + days);
    return d.toISOString();
  };

  const fullUrl = (path: string) => `${window.location.origin}${path}`;

  const createPackage = async () => {
    if (!animalId || !study) return;
    setCreating(true);
    try {
      await apiClient.createReferralPackage({
        animal_patient_id: animalId,
        study_uid: study.StudyInstanceUID,
        reason: reason || undefined,
        history_summary: historySummary || undefined,
        urgency,
        expires_at: computeExpiry(),
        recipient_email: recipientEmail || undefined,
      });
      setReason('');
      setHistorySummary('');
      setRecipientEmail('');
      toast.success(t('referral.created'));
      load();
    } catch {
      toast.error(t('referral.createFailed'));
    } finally {
      setCreating(false);
    }
  };

  const copyLink = async (path: string) => {
    const url = fullUrl(path);
    try {
      await navigator.clipboard.writeText(url);
      toast.success(t('referral.copied'));
    } catch {
      window.prompt(t('referral.copy'), url);
    }
  };

  const revoke = async (id: number) => {
    try {
      await apiClient.deleteReferralPackage(id);
      toast.success(t('referral.revoked'));
      load();
    } catch {
      toast.error(t('referral.revokeFailed'));
    }
  };

  const selectCls =
    'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-medical-500 text-sm';

  return (
    <Modal isOpen={study != null} onClose={onClose} title={t('referral.title')} size="md">
      <ModalContent>
        <p className="text-sm text-slate-500 mb-4">{t('referral.subtitle')}</p>

        {!animalId ? (
          <p className="text-sm text-amber-600 dark:text-amber-400">{t('referral.noPatient')}</p>
        ) : (
          <>
            {/* New-package form */}
            <div className="space-y-3 rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('referral.reason')}</label>
                <textarea className={`${selectCls} h-20`} value={reason}
                  placeholder={t('referral.reasonPlaceholder')}
                  onChange={(e) => setReason(e.target.value)} />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('referral.historySummary')}</label>
                <textarea className={`${selectCls} h-20`} value={historySummary}
                  placeholder={t('referral.historyPlaceholder')}
                  onChange={(e) => setHistorySummary(e.target.value)} />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('referral.urgency')}</label>
                  <select className={selectCls} value={urgency}
                    onChange={(e) => setUrgency(e.target.value as ReferralUrgency)}>
                    {URGENCIES.map((u) => <option key={u} value={u}>{t(`referral.urgencies.${u}`)}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('referral.expiry')}</label>
                  <select className={selectCls} value={expiry} onChange={(e) => setExpiry(e.target.value as ExpiryOption)}>
                    <option value="7">{t('referral.expiry7')}</option>
                    <option value="30">{t('referral.expiry30')}</option>
                    <option value="never">{t('referral.expiryNever')}</option>
                  </select>
                </div>
              </div>
              <Input label={t('referral.recipientEmail')} type="email" value={recipientEmail}
                onChange={(e) => setRecipientEmail(e.target.value)} />
              <div className="flex justify-end">
                <Button variant="medical" leftIcon={Send} onClick={createPackage} disabled={creating}>
                  {creating ? t('referral.creating') : t('referral.create')}
                </Button>
              </div>
            </div>

            {/* Existing packages */}
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">{t('referral.existing')}</h4>
            {packages.length === 0 ? (
              <p className="text-sm text-slate-400">{t('referral.none')}</p>
            ) : (
              <ul className="divide-y divide-slate-100 dark:divide-slate-700">
                {packages.map((pkg) => (
                  <li key={pkg.id} className="flex items-center justify-between gap-2 py-2">
                    <div className="min-w-0 flex-1">
                      <div className="font-mono text-xs text-slate-600 dark:text-slate-300 truncate">{fullUrl(pkg.share_path)}</div>
                      <div className="text-xs text-slate-400">
                        {t(`referral.urgencies.${pkg.urgency}`)}
                        {' · '}
                        {t('referral.accessCount', { count: pkg.access_count })}
                        {' · '}
                        {pkg.expires_at
                          ? t('referral.expiresOn', { date: new Date(pkg.expires_at).toLocaleDateString() })
                          : t('referral.neverExpires')}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        className="p-2 text-slate-400 hover:text-medical-600 transition-colors"
                        onClick={() => copyLink(pkg.share_path)}
                        title={t('referral.copy')}
                        aria-label={t('referral.copy')}
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      <button
                        className="p-2 text-slate-400 hover:text-error-500 transition-colors"
                        onClick={() => revoke(pkg.id)}
                        title={t('referral.revoke')}
                        aria-label={t('referral.revoke')}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </ModalContent>
      <ModalFooter>
        <Button variant="ghost" onClick={onClose}>{t('referral.close')}</Button>
      </ModalFooter>
    </Modal>
  );
};

export default ReferralModal;
