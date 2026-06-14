/**
 * AssignPatientModal — assign (or unassign) a DICOM study to an animal patient.
 * Calls apiClient.linkStudyToAnimal and notifies the parent on success.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { apiClient, type AnimalPatientListItem } from '../../utils/api';
import { Modal, ModalContent, ModalFooter, Button } from '../ui';
import PatientPicker from './PatientPicker';

interface AssignPatientModalProps {
  studyUID: string | null;
  currentPatientName?: string | null;
  onClose: () => void;
  onAssigned: (animal: AnimalPatientListItem | null) => void;
}

const AssignPatientModal: React.FC<AssignPatientModalProps> = ({
  studyUID, currentPatientName, onClose, onAssigned,
}) => {
  const { t } = useTranslation('patients');
  const [saving, setSaving] = useState(false);

  const assign = async (animal: AnimalPatientListItem | null) => {
    if (!studyUID) return;
    setSaving(true);
    try {
      await apiClient.linkStudyToAnimal(studyUID, animal ? animal.id : null);
      toast.success(animal
        ? t('assign.linked', { name: animal.name, defaultValue: `Linked to {{name}}` })
        : t('assign.unlinked', 'Study unlinked'));
      onAssigned(animal);
      onClose();
    } catch {
      toast.error(t('assign.failed', 'Failed to update study link'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={studyUID != null} onClose={onClose} title={t('assign.title', 'Assign study to patient')} size="md">
      <ModalContent>
        {currentPatientName && (
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">
            {t('assign.current', 'Currently linked to')}:{' '}
            <span className="font-medium text-slate-800 dark:text-slate-100">{currentPatientName}</span>
          </p>
        )}
        <PatientPicker autoFocus onSelect={assign} />
      </ModalContent>
      <ModalFooter>
        <Button variant="ghost" onClick={onClose} disabled={saving}>{t('assign.cancel', 'Cancel')}</Button>
        {currentPatientName && (
          <Button variant="outline" onClick={() => assign(null)} disabled={saving}>
            {t('assign.unassign', 'Unassign')}
          </Button>
        )}
      </ModalFooter>
    </Modal>
  );
};

export default AssignPatientModal;
