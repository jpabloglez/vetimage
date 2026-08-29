/**
 * TagEditorImagePicker
 *
 * Study -> Series -> Instance cascade so the standalone Tag Editor tool has
 * a real image to edit, instead of always rendering its empty state.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { apiClient } from '../../utils/api';
import type { Study, Series, Instance } from '../../types/api';

interface TagEditorImagePickerProps {
  onSelect: (imageId: number | null) => void;
}

const selectClasses = 'w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-medical-500 disabled:opacity-50';

export const TagEditorImagePicker: React.FC<TagEditorImagePickerProps> = ({ onSelect }) => {
  const { t } = useTranslation('tools');
  const [studies, setStudies] = useState<Study[]>([]);
  const [series, setSeries] = useState<Series[]>([]);
  const [instances, setInstances] = useState<Instance[]>([]);
  const [studyUID, setStudyUID] = useState('');
  const [seriesUID, setSeriesUID] = useState('');
  const [instanceId, setInstanceId] = useState('');

  useEffect(() => {
    apiClient.getStudies().then(setStudies).catch(() => toast.error(t('tagEditor.loadStudiesError')));
  }, [t]);

  useEffect(() => {
    setSeries([]);
    setSeriesUID('');
    setInstances([]);
    setInstanceId('');
    onSelect(null);
    if (!studyUID) return;
    apiClient.getSeries(studyUID).then(setSeries).catch(() => toast.error(t('tagEditor.loadStudiesError')));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studyUID]);

  useEffect(() => {
    setInstances([]);
    setInstanceId('');
    onSelect(null);
    if (!studyUID || !seriesUID) return;
    apiClient.getInstances(studyUID, seriesUID).then(setInstances).catch(() => toast.error(t('tagEditor.loadStudiesError')));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seriesUID]);

  const handleInstanceChange = (value: string) => {
    setInstanceId(value);
    onSelect(value ? Number(value) : null);
  };

  return (
    <div className="medical-card p-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div>
        <label htmlFor="tag-editor-study" className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
          {t('tagEditor.study')}
        </label>
        <select id="tag-editor-study" className={selectClasses} value={studyUID} onChange={(e) => setStudyUID(e.target.value)}>
          <option value="">{t('tagEditor.selectStudy')}</option>
          {studies.map((s) => (
            <option key={s.StudyInstanceUID} value={s.StudyInstanceUID}>
              {s.PatientName || s.PatientID} — {s.StudyDescription || s.StudyDate}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="tag-editor-series" className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
          {t('tagEditor.series')}
        </label>
        <select
          id="tag-editor-series"
          className={selectClasses}
          value={seriesUID}
          onChange={(e) => setSeriesUID(e.target.value)}
          disabled={!studyUID}
        >
          <option value="">{t('tagEditor.selectSeries')}</option>
          {series.map((s) => (
            <option key={s.SeriesInstanceUID} value={s.SeriesInstanceUID}>
              {s.Modality} — {s.SeriesDescription || `#${s.SeriesNumber}`}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="tag-editor-instance" className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
          {t('tagEditor.instance')}
        </label>
        <select
          id="tag-editor-instance"
          className={selectClasses}
          value={instanceId}
          onChange={(e) => handleInstanceChange(e.target.value)}
          disabled={!seriesUID}
        >
          <option value="">{t('tagEditor.selectInstance')}</option>
          {instances.map((i) => (
            <option key={i.id} value={i.id}>
              #{i.InstanceNumber} — {i.SOPInstanceUID.slice(-12)}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default TagEditorImagePicker;
