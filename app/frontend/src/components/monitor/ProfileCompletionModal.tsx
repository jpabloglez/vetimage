/**
 * Profile Completion Modal
 *
 * Modal form for completing user profile with department, job title, team,
 * and job sharing preferences for the Monitor page.
 */

import React, { useState } from 'react';
import { X, Building2, Briefcase, Users, Shield } from 'lucide-react';
import { apiClient, ProfileCompletionData } from '../../utils/api';
import Button from '../ui/Button';
import toast from 'react-hot-toast';

interface ProfileCompletionModalProps {
  onClose: () => void;
  onComplete?: () => void;
}

export const ProfileCompletionModal: React.FC<ProfileCompletionModalProps> = ({
  onClose,
  onComplete,
}) => {
  const [formData, setFormData] = useState<ProfileCompletionData>({
    department: '',
    job_title: '',
    team_name: '',
    is_sharing_jobs_with_colleagues: false,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.department || !formData.job_title) {
      toast.error('Department and Job Title are required');
      return;
    }

    setIsSubmitting(true);

    try {
      await apiClient.completeProfile(formData);
      toast.success('Profile updated successfully');
      onComplete?.();
      onClose();
    } catch (error: any) {
      console.error('Failed to complete profile:', error);
      toast.error(error.message || 'Failed to update profile');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            Complete Your Profile
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Info Banner */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              This information helps you track analysis jobs within your department and team.
            </p>
          </div>

          {/* Department */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              <Building2 className="w-4 h-4" />
              Department / Division *
            </label>
            <input
              type="text"
              required
              value={formData.department}
              onChange={(e) =>
                setFormData({ ...formData, department: e.target.value })
              }
              placeholder="e.g., Radiology, Cardiology"
              className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-medical-500 focus:border-transparent"
            />
          </div>

          {/* Job Title */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              <Briefcase className="w-4 h-4" />
              Job Title / Role *
            </label>
            <input
              type="text"
              required
              value={formData.job_title}
              onChange={(e) =>
                setFormData({ ...formData, job_title: e.target.value })
              }
              placeholder="e.g., Radiologist, Technician"
              className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-medical-500 focus:border-transparent"
            />
          </div>

          {/* Team Name (Optional) */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              <Users className="w-4 h-4" />
              Team / Workspace (optional)
            </label>
            <input
              type="text"
              value={formData.team_name}
              onChange={(e) =>
                setFormData({ ...formData, team_name: e.target.value })
              }
              placeholder="e.g., MRI Team, Research Group"
              className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-medical-500 focus:border-transparent"
            />
          </div>

          {/* Job Sharing Preference */}
          <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-4">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_sharing_jobs_with_colleagues}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    is_sharing_jobs_with_colleagues: e.target.checked,
                  })
                }
                className="mt-1 w-4 h-4 text-medical-600 border-slate-300 rounded focus:ring-medical-500"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-900 dark:text-white mb-1">
                  <Shield className="w-4 h-4" />
                  Share my analysis jobs with colleagues
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Allow colleagues in your organization to view your analysis jobs on the
                  Monitor page. Your name and department will be visible to them.
                </p>
              </div>
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting}
              className="flex-1"
            >
              {isSubmitting ? 'Saving...' : 'Save Profile'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
