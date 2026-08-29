/**
 * DicomTagReviewStep
 *
 * Wizard step shown right after upload, before AI dispatch: lets the user
 * confirm/correct the study's PatientName/PatientID/AccessionNumber. Saving
 * writes these to the MedicalStudy row AND to every on-disk instance file
 * (via apiClient.updateStudyTagReview), so the DICOM files themselves never
 * disagree with what the app displays.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

import { apiClient } from '../../utils/api';
import type { StudyTagReviewFields } from '../../types/api';
import Button from '../ui/Button';

interface DicomTagReviewStepProps {
  studyUID: string;
  onContinue: () => void;
  onBack: () => void;
}

const EMPTY_FIELDS: StudyTagReviewFields = {
  patient_name: '',
  patient_id: '',
  accession_number: '',
};

export const DicomTagReviewStep: React.FC<DicomTagReviewStepProps> = ({ studyUID, onContinue, onBack }) => {
  const { t } = useTranslation('analyze');
  const [fields, setFields] = useState<StudyTagReviewFields>(EMPTY_FIELDS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiClient
      .getStudyTagReview(studyUID)
      .then((data) => !cancelled && setFields(data))
      .catch(() => !cancelled && toast.error(t('reviewTags.loadError')))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [studyUID, t]);

  const handleChange = (field: keyof StudyTagReviewFields) => (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    setFields((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleContinue = async () => {
    setSaving(true);
    try {
      await apiClient.updateStudyTagReview(studyUID, fields);
      onContinue();
    } catch {
      toast.error(t('reviewTags.saveError'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <Button variant="ghost" onClick={onBack}>{t('backToUpload')}</Button>

      <div className="medical-card p-6 max-w-2xl">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-1">
          {t('reviewTags.title')}
        </h3>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          {t('reviewTags.description')}
        </p>

        {loading ? (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label htmlFor="review-patient-name" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t('reviewTags.patientName')}
              </label>
              <input
                id="review-patient-name"
                type="text"
                value={fields.patient_name}
                onChange={handleChange('patient_name')}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-medical-500"
              />
            </div>
            <div>
              <label htmlFor="review-patient-id" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t('reviewTags.patientId')}
              </label>
              <input
                id="review-patient-id"
                type="text"
                value={fields.patient_id}
                onChange={handleChange('patient_id')}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-medical-500"
              />
            </div>
            <div>
              <label htmlFor="review-accession-number" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t('reviewTags.accessionNumber')}
              </label>
              <input
                id="review-accession-number"
                type="text"
                value={fields.accession_number}
                onChange={handleChange('accession_number')}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-medical-500"
              />
            </div>

            <div className="pt-2">
              <Button onClick={handleContinue} disabled={saving} loading={saving}>
                {t('reviewTags.continue')}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DicomTagReviewStep;
