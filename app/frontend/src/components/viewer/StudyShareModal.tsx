/**
 * StudyShareModal — create and manage token-gated share links for a DICOM study.
 *
 * Lets a clinician generate an unguessable link (optionally time-limited or
 * view-limited) that an external vet or specialist can open without a login.
 * Existing links for the study are listed with copy / revoke actions.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Copy, Trash2, Link2 } from 'lucide-react';
import { apiClient, type Study, type StudyShareLink } from '../../utils/api';
import { Button, Input, Modal, ModalContent, ModalFooter } from '../ui';

interface StudyShareModalProps {
  study: Study | null;
  onClose: () => void;
}

type ExpiryOption = '7' | '30' | 'never';

const StudyShareModal: React.FC<StudyShareModalProps> = ({ study, onClose }) => {
  const { t } = useTranslation('viewer');
  const [links, setLinks] = useState<StudyShareLink[]>([]);
  const [expiry, setExpiry] = useState<ExpiryOption>('30');
  const [maxAccesses, setMaxAccesses] = useState<string>('');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [creating, setCreating] = useState(false);

  const studyUid = study?.StudyInstanceUID ?? null;

  const load = useCallback(() => {
    if (!studyUid) { setLinks([]); return; }
    apiClient.getStudyShareLinks(studyUid).then(setLinks).catch(() => setLinks([]));
  }, [studyUid]);

  useEffect(() => { load(); }, [load]);

  const computeExpiry = (): string | null => {
    if (expiry === 'never') return null;
    const days = expiry === '7' ? 7 : 30;
    const d = new Date();
    d.setDate(d.getDate() + days);
    return d.toISOString();
  };

  const createLink = async () => {
    if (!studyUid) return;
    setCreating(true);
    try {
      await apiClient.createStudyShareLink({
        study_uid: studyUid,
        expires_at: computeExpiry(),
        max_accesses: maxAccesses ? Number(maxAccesses) : null,
        recipient_email: recipientEmail || undefined,
      });
      setMaxAccesses('');
      setRecipientEmail('');
      load();
    } catch {
      toast.error(t('share.createFailed'));
    } finally {
      setCreating(false);
    }
  };

  const copyLink = async (url?: string) => {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      toast.success(t('share.copied'));
    } catch {
      // Clipboard API can fail in insecure contexts; surface the URL via prompt fallback.
      window.prompt(t('share.copy'), url);
    }
  };

  const revoke = async (id: number) => {
    try {
      await apiClient.deleteStudyShareLink(id);
      toast.success(t('share.revoked'));
      load();
    } catch {
      toast.error(t('share.revokeFailed'));
    }
  };

  const selectCls =
    'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-medical-500 text-sm';

  return (
    <Modal isOpen={study != null} onClose={onClose} title={t('share.title')} size="md">
      <ModalContent>
        <p className="text-sm text-slate-500 mb-4">{t('share.subtitle')}</p>

        {/* New-link form */}
        <div className="space-y-3 rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('share.expiry')}</label>
              <select className={selectCls} value={expiry} onChange={(e) => setExpiry(e.target.value as ExpiryOption)}>
                <option value="7">{t('share.expiry7')}</option>
                <option value="30">{t('share.expiry30')}</option>
                <option value="never">{t('share.expiryNever')}</option>
              </select>
            </div>
            <Input
              label={t('share.maxAccesses')}
              type="number"
              min="1"
              value={maxAccesses}
              onChange={(e) => setMaxAccesses(e.target.value)}
            />
          </div>
          <Input
            label={t('share.recipientEmail')}
            type="email"
            value={recipientEmail}
            onChange={(e) => setRecipientEmail(e.target.value)}
          />
          <div className="flex justify-end">
            <Button variant="medical" leftIcon={Link2} onClick={createLink} disabled={creating}>
              {creating ? t('share.creating') : t('share.create')}
            </Button>
          </div>
        </div>

        {/* Existing links */}
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">{t('share.existingLinks')}</h4>
        {links.length === 0 ? (
          <p className="text-sm text-slate-400">{t('share.noLinks')}</p>
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-700">
            {links.map((link) => (
              <li key={link.id} className="flex items-center justify-between gap-2 py-2">
                <div className="min-w-0 flex-1">
                  <div className="font-mono text-xs text-slate-600 dark:text-slate-300 truncate">{link.share_url}</div>
                  <div className="text-xs text-slate-400">
                    {t('share.accessCount', { count: link.access_count })}
                    {' · '}
                    {link.expires_at
                      ? t('share.expiresOn', { date: new Date(link.expires_at).toLocaleDateString() })
                      : t('share.neverExpires')}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    className="p-2 text-slate-400 hover:text-medical-600 transition-colors"
                    onClick={() => copyLink(link.share_url)}
                    title={t('share.copy')}
                    aria-label={t('share.copy')}
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    className="p-2 text-slate-400 hover:text-error-500 transition-colors"
                    onClick={() => revoke(link.id)}
                    title={t('share.revoke')}
                    aria-label={t('share.revoke')}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </ModalContent>
      <ModalFooter>
        <Button variant="ghost" onClick={onClose}>{t('share.close')}</Button>
      </ModalFooter>
    </Modal>
  );
};

export default StudyShareModal;
