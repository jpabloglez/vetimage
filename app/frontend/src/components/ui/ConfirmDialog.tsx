/**
 * ConfirmDialog — a styled, translatable confirmation modal to replace
 * window.confirm(). Used for destructive actions (delete owner/patient/VHS).
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import Modal, { ModalContent, ModalFooter } from './Modal';
import Button from './Button';

interface ConfirmDialogProps {
  open: boolean;
  message: string;
  title?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open, message, title, confirmLabel, cancelLabel, danger, onConfirm, onCancel,
}) => {
  const { t } = useTranslation('common');
  return (
    <Modal isOpen={open} onClose={onCancel} title={title ?? t('buttons.confirm', 'Confirm')} size="sm">
      <ModalContent>
        <p className="text-slate-700 dark:text-slate-300">{message}</p>
      </ModalContent>
      <ModalFooter>
        <Button variant="ghost" onClick={onCancel}>{cancelLabel ?? t('buttons.cancel', 'Cancel')}</Button>
        <Button variant={danger ? 'danger' : 'medical'} onClick={onConfirm}>
          {confirmLabel ?? t('buttons.confirm', 'Confirm')}
        </Button>
      </ModalFooter>
    </Modal>
  );
};

export default ConfirmDialog;
