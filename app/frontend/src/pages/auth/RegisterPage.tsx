import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  User,
  Building,
  Stethoscope,
  UserPlus,
  CheckCircle,
} from 'lucide-react';
import { toast } from 'react-hot-toast';

import { Button, Input, Card, CardHeader, CardTitle, CardContent } from '../../components/ui';
import { useAuth } from '../../contexts';
import { registrationSchema, RegistrationFormData } from '../../utils/validation';

const RegisterPage: React.FC = () => {
  const { register: registerUser, isLoading } = useAuth();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const { t } = useTranslation('auth');

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegistrationFormData>({
    resolver: zodResolver(registrationSchema),
    defaultValues: {
      role: 'doctor',
    },
  });

  const selectedRole = watch('role');

  const onSubmit = async (data: RegistrationFormData) => {
    try {
      await registerUser(data.email, data.password, data.confirmPassword);
      toast.success(t('register.toastSuccess'));
      navigate('/models');
    } catch (error: any) {
      console.error('Registration error:', error);
      toast.error(error.message || t('register.toastError'));
    }
  };

  return (
    <div className="min-h-screen bg-gradient-medical dark:bg-gradient-medical-dark flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div className="mx-auto w-16 h-16 bg-medical-500 rounded-full flex items-center justify-center mb-4">
            <Stethoscope className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold medical-gradient-text">{t('login.brand')}</h1>
          <p className="text-slate-600 dark:text-slate-400 mt-2">
            {t('login.brandTagline')}
          </p>
        </div>

        <Card variant="medical" className="animate-fade-in">
          <CardHeader>
            <CardTitle className="text-center">{t('register.title')}</CardTitle>
            <p className="text-center text-slate-600 dark:text-slate-400 mt-2">
              {t('register.subtitle')}
            </p>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* Name Input */}
              <Input
                {...register('name')}
                type="text"
                label={t('register.fullName')}
                leftIcon={User}
                error={errors.name?.message}
                placeholder="Dr. John Smith"
                required
                disabled={isSubmitting}
              />

              {/* Email Input */}
              <Input
                {...register('email')}
                type="email"
                label={t('register.email')}
                leftIcon={Mail}
                error={errors.email?.message}
                placeholder="vet@clinic.com"
                required
                disabled={isSubmitting}
              />

              {/* Role Selection */}
              <div className="space-y-2">
                <label htmlFor="role" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  {t('register.role')} <span className="text-error-500">*</span>
                </label>
                <select
                  {...register('role')}
                  id="role"
                  className="medical-input"
                  disabled={isSubmitting}
                >
                  <option value="doctor">{t('register.roleDoctor')}</option>
                  <option value="researcher">{t('register.roleResearcher')}</option>
                  <option value="user">{t('register.roleMedStudent')}</option>
                </select>
                {errors.role && (
                  <p className="text-sm text-error-600 dark:text-error-400">
                    {errors.role.message}
                  </p>
                )}
              </div>

              {/* Institution Input */}
              <Input
                {...register('institution')}
                type="text"
                label={t('register.institution')}
                leftIcon={Building}
                error={errors.institution?.message}
                placeholder="Your veterinary clinic"
                helper={t('register.institutionPlaceholder')}
                disabled={isSubmitting}
              />

              {/* Specialization (if doctor) */}
              {selectedRole === 'doctor' && (
                <Input
                  {...register('specialization')}
                  type="text"
                  label={t('register.specialization')}
                  leftIcon={Stethoscope}
                  error={errors.specialization?.message}
                  placeholder={t('register.specializationPlaceholder')}
                  helper={t('register.specialization')}
                  disabled={isSubmitting}
                />
              )}

              {/* Research Area (if researcher) */}
              {selectedRole === 'researcher' && (
                <Input
                  {...register('specialization')}
                  type="text"
                  label={t('register.researchArea')}
                  leftIcon={Stethoscope}
                  error={errors.specialization?.message}
                  placeholder={t('register.researchAreaPlaceholder')}
                  helper={t('register.researchArea')}
                  disabled={isSubmitting}
                />
              )}

              {/* Password Input */}
              <div className="relative">
                <Input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  label={t('register.password')}
                  leftIcon={Lock}
                  error={errors.password?.message}
                  placeholder={t('register.passwordPlaceholder')}
                  required
                  disabled={isSubmitting}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-9 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  disabled={isSubmitting}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>

              {/* Confirm Password Input */}
              <div className="relative">
                <Input
                  {...register('confirmPassword')}
                  type={showConfirmPassword ? 'text' : 'password'}
                  label={t('register.confirmPassword')}
                  leftIcon={Lock}
                  error={errors.confirmPassword?.message}
                  placeholder="Confirm your password"
                  required
                  disabled={isSubmitting}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-9 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  disabled={isSubmitting}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>

              {/* Terms and Conditions */}
              <div className="space-y-2">
                <label className="flex items-start space-x-3">
                  <input
                    {...register('terms')}
                    type="checkbox"
                    className="rounded border-slate-300 text-medical-500 focus:ring-medical-500 mt-1"
                    disabled={isSubmitting}
                  />
                  <span className="text-sm text-slate-600 dark:text-slate-400">
                    {t('register.termsAgreement')}
                  </span>
                </label>
                {errors.terms && (
                  <p className="text-sm text-error-600 dark:text-error-400 ml-6">
                    {errors.terms.message}
                  </p>
                )}
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="medical"
                size="lg"
                fullWidth
                loading={isSubmitting || isLoading}
                leftIcon={UserPlus}
              >
                {isSubmitting || isLoading ? t('register.submitting') : t('register.submit')}
              </Button>

              {/* Sign In Link */}
              <div className="text-center">
                <span className="text-slate-600 dark:text-slate-400">
                  {t('register.hasAccount')}{' '}
                  <Link
                    to="/auth/login"
                    className="text-medical-600 hover:text-medical-500 dark:text-medical-400 dark:hover:text-medical-300 font-medium"
                  >
                    {t('register.signIn')}
                  </Link>
                </span>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center mt-8 text-sm text-slate-500 dark:text-slate-400">
          <p>{t('register.copyright', { year: new Date().getFullYear() })}</p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;