/**
 * Profile Settings Modal
 *
 * Modal for editing user profile information including:
 * - Email (read-only)
 * - Department
 * - Job Title
 * - Team Name
 * - Preferred Language
 * - Password change option
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'react-hot-toast';
import { Modal, ModalHeader, ModalContent, ModalFooter } from '../ui';
import { Button } from '../ui';
import { Input } from '../ui';
import { useAuth } from '../../contexts/AuthContext';
import { useLanguage } from '../../contexts/LanguageContext';
import { apiClient } from '../../utils/api';
import { User, Lock } from 'lucide-react';

interface ProfileSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ProfileFormData {
  department: string;
  job_title: string;
  team_name: string;
  is_sharing_jobs_with_colleagues: boolean;
  language: string;
}

export const ProfileSettingsModal: React.FC<ProfileSettingsModalProps> = ({
  isOpen,
  onClose
}) => {
  const { t } = useTranslation('profile');
  const { user, refreshUser } = useAuth();
  const { currentLanguage, setLanguage, languages } = useLanguage();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState<ProfileFormData>({
    department: '',
    job_title: '',
    team_name: '',
    is_sharing_jobs_with_colleagues: false,
    language: currentLanguage
  });

  // Load current profile data
  useEffect(() => {
    const loadProfile = async () => {
      if (isOpen && user) {
        try {
          const profile = await apiClient.getProfile() as any;
          setFormData({
            department: profile.department || '',
            job_title: profile.job_title || '',
            team_name: profile.team_name || '',
            is_sharing_jobs_with_colleagues: profile.is_sharing_jobs_with_colleagues || false,
            language: profile.language || currentLanguage
          });
        } catch (error) {
          console.error('Failed to load profile:', error);
        }
      }
    };

    loadProfile();
  }, [isOpen, user, currentLanguage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await apiClient.completeProfile(formData);
      // Apply language immediately
      if (formData.language !== currentLanguage) {
        setLanguage(formData.language);
      }
      await refreshUser();
      toast.success(t('settings.updateSuccess'));
      onClose();
    } catch (error: any) {
      console.error('Failed to update profile:', error);
      toast.error(error.message || t('settings.updateError'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (field: keyof ProfileFormData, value: string | boolean) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <form onSubmit={handleSubmit}>
        <ModalHeader>
          <div className="flex items-center gap-2">
            <User className="w-5 h-5 text-medical-600 dark:text-medical-400" />
            <span>{t('settings.title')}</span>
          </div>
        </ModalHeader>

        <ModalContent>
          <div className="space-y-4">
            {/* Email (Read-only) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('settings.email')}
              </label>
              <Input
                type="email"
                value={user?.email || ''}
                disabled
                className="bg-gray-50 dark:bg-gray-900"
              />
              <p className="text-xs text-gray-500 mt-1">
                {t('settings.emailReadonly')}
              </p>
            </div>

            {/* Role (Read-only) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('settings.role', { defaultValue: 'Role' })}
              </label>
              <Input
                type="text"
                value={user?.role || ''}
                disabled
                className="bg-gray-50 dark:bg-gray-900"
              />
            </div>

            {/* Department */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('settings.department')}
              </label>
              <Input
                type="text"
                value={formData.department}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange('department', e.target.value)}
                placeholder={t('settings.departmentPlaceholder')}
              />
            </div>

            {/* Job Title */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('settings.jobTitle')}
              </label>
              <Input
                type="text"
                value={formData.job_title}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange('job_title', e.target.value)}
                placeholder={t('settings.jobTitlePlaceholder')}
              />
            </div>

            {/* Team Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('settings.teamWorkspace')} <span className="text-gray-400">({t('common:labels.optional')})</span>
              </label>
              <Input
                type="text"
                value={formData.team_name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange('team_name', e.target.value)}
                placeholder={t('settings.teamPlaceholder')}
              />
            </div>

            {/* Preferred Language */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('settings.preferredLanguage')}
              </label>
              <select
                value={formData.language}
                onChange={(e) => handleChange('language', e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:ring-2 focus:ring-medical-500 focus:border-medical-500"
              >
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.flag} {lang.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">
                {t('settings.languageHelp')}
              </p>
            </div>

            {/* Job Sharing Preference */}
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                id="jobSharing"
                checked={formData.is_sharing_jobs_with_colleagues}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange('is_sharing_jobs_with_colleagues', e.target.checked)}
                className="mt-1 h-4 w-4 text-medical-600 focus:ring-medical-500 border-gray-300 rounded"
              />
              <div>
                <label
                  htmlFor="jobSharing"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer"
                >
                  {t('settings.shareJobs')}
                </label>
                <p className="text-xs text-gray-500 mt-1">
                  {t('settings.shareJobsDesc')}
                </p>
              </div>
            </div>

            {/* Password Change Button */}
            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button
                type="button"
                variant="outline"
                leftIcon={Lock}
                onClick={() => toast('Password change functionality coming soon', { icon: '🔐' })}
                fullWidth
              >
                {t('settings.changePassword')}
              </Button>
            </div>
          </div>
        </ModalContent>

        <ModalFooter>
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
          >
            {t('settings.cancel')}
          </Button>
          <Button
            type="submit"
            variant="medical"
            loading={isLoading}
          >
            {t('settings.saveChanges')}
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  );
};
