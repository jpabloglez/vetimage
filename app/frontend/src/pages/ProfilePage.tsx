/**
 * Profile Page
 *
 * User profile page with inline settings form and avatar upload.
 */

import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'react-hot-toast';
import { Camera, Mail, Briefcase, Users, Globe } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { apiClient } from '../utils/api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui';
import { Button } from '../components/ui';
import { Input } from '../components/ui';

const getRoleName = (role: number | undefined, t: (key: string) => string): string => {
  const map: Record<number, string> = {
    1: t('common:roles.user'),
    2: t('common:roles.guest'),
    3: t('common:roles.admin'),
    4: t('common:roles.manager'),
    5: t('common:roles.superuser'),
  };
  return map[role ?? 1] ?? t('common:roles.user');
};

interface ProfileFormData {
  department: string;
  job_title: string;
  team_name: string;
  is_sharing_jobs_with_colleagues: boolean;
  language: string;
}

export const ProfilePage: React.FC = () => {
  const { t } = useTranslation('profile');
  const { user, refreshUser } = useAuth();
  const { currentLanguage, setLanguage, languages } = useLanguage();

  const [imageUrl, setImageUrl] = useState<string | undefined>(user?.image_url);
  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [formData, setFormData] = useState<ProfileFormData>({
    department: '',
    job_title: '',
    team_name: '',
    is_sharing_jobs_with_colleagues: false,
    language: currentLanguage,
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync avatar URL from user context
  useEffect(() => {
    if (user?.image_url) setImageUrl(user.image_url);
  }, [user?.image_url]);

  // Load profile fields on mount
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const profile = await apiClient.getProfile() as any;
        setFormData({
          department: profile.department || '',
          job_title: profile.job_title || '',
          team_name: profile.team_name || '',
          is_sharing_jobs_with_colleagues: profile.is_sharing_jobs_with_colleagues || false,
          language: profile.language || currentLanguage,
        });
        if (profile.image_url) setImageUrl(profile.image_url);
      } catch (error) {
        console.error('Failed to load profile:', error);
      }
    };
    loadProfile();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error(t('avatar.invalidType'));
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error(t('avatar.sizeTooLarge'));
      return;
    }

    setIsUploading(true);
    try {
      const result = await apiClient.uploadAvatar(file);
      setImageUrl(result.image_url);
      await refreshUser();
      toast.success(t('avatar.uploadSuccess'));
    } catch (error: any) {
      toast.error(error?.detail || t('avatar.uploadError'));
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await apiClient.completeProfile(formData);
      if (formData.language !== currentLanguage) {
        setLanguage(formData.language);
      }
      await refreshUser();
      toast.success(t('form.saveSuccess'));
    } catch (error: any) {
      toast.error(error?.message || t('form.saveError'));
    } finally {
      setIsSaving(false);
    }
  };

  const handleChange = <K extends keyof ProfileFormData>(field: K, value: ProfileFormData[K]) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const initials = user?.email?.split('@')[0]?.slice(0, 2).toUpperCase() || 'U';

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          {t('title')}
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          {t('subtitle')}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column — Avatar + identity card */}
        <div className="lg:col-span-1">
          <Card variant="elevated">
            <CardContent className="pt-6">
              <div className="text-center">
                {/* Clickable avatar */}
                <div className="relative inline-block mx-auto mb-2">
                  <button
                    type="button"
                    onClick={handleAvatarClick}
                    disabled={isUploading}
                    title={t('avatar.changePhoto')}
                    className="w-24 h-24 rounded-full overflow-hidden bg-gradient-to-br from-medical-500 to-medical-600 flex items-center justify-center relative group focus:outline-none focus:ring-2 focus:ring-medical-500 focus:ring-offset-2"
                  >
                    {imageUrl ? (
                      <img
                        src={imageUrl}
                        alt="Avatar"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <span className="text-2xl font-bold text-white">{initials}</span>
                    )}
                    {/* Hover overlay */}
                    <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity rounded-full">
                      {isUploading ? (
                        <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <Camera className="w-6 h-6 text-white" />
                      )}
                    </div>
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                </div>

                <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                  {isUploading ? t('avatar.uploading') : t('avatar.uploadHint')}
                </p>

                {/* User identity */}
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-1">
                  {user?.email?.split('@')[0] || 'User'}
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  {user?.email}
                </p>

                {/* Role badge */}
                <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-medical-100 dark:bg-medical-900/30 text-medical-800 dark:text-medical-200">
                  {getRoleName(user?.role, t)}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right column — Inline settings form */}
        <div className="lg:col-span-2">
          <Card variant="elevated">
            <CardHeader>
              <CardTitle>{t('settings.title')}</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Email (read-only) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    <span className="flex items-center gap-2">
                      <Mail className="w-4 h-4" />
                      {t('settings.email')}
                    </span>
                  </label>
                  <Input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="bg-gray-50 dark:bg-gray-900"
                  />
                  <p className="text-xs text-gray-500 mt-1">{t('settings.emailReadonly')}</p>
                </div>

                {/* Department */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    <span className="flex items-center gap-2">
                      <Briefcase className="w-4 h-4" />
                      {t('settings.department')}
                    </span>
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
                    <span className="flex items-center gap-2">
                      <Briefcase className="w-4 h-4" />
                      {t('settings.jobTitle')}
                    </span>
                  </label>
                  <Input
                    type="text"
                    value={formData.job_title}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange('job_title', e.target.value)}
                    placeholder={t('settings.jobTitlePlaceholder')}
                  />
                </div>

                {/* Team / Workspace */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    <span className="flex items-center gap-2">
                      <Users className="w-4 h-4" />
                      {t('settings.teamWorkspace')}
                      <span className="text-gray-400 font-normal">({t('common:labels.optional')})</span>
                    </span>
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
                    <span className="flex items-center gap-2">
                      <Globe className="w-4 h-4" />
                      {t('settings.preferredLanguage')}
                    </span>
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
                </div>

                {/* Job sharing toggle */}
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
                    <p className="text-xs text-gray-500 mt-1">{t('settings.shareJobsDesc')}</p>
                  </div>
                </div>

                {/* Save button */}
                <div className="pt-4">
                  <Button type="submit" variant="medical" loading={isSaving} fullWidth>
                    {isSaving ? t('form.saving') : t('form.saveChanges')}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
