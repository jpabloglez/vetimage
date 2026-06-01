import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Lock, Eye, EyeOff, CheckCircle, AlertCircle, Stethoscope } from 'lucide-react';
import { toast } from 'react-hot-toast';

import { Button, Input, Card, CardHeader, CardTitle, CardContent } from '../../components/ui';
import { useAuth } from '../../contexts';
import { resetPasswordSchema, ResetPasswordFormData } from '../../utils/validation';

const ResetPasswordPage: React.FC = () => {
  const { resetPassword } = useAuth();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation('auth');

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [resetComplete, setResetComplete] = useState(false);
  const [tokenValid, setTokenValid] = useState<boolean | null>(null);

  const token = searchParams.get('token');
  const uid   = searchParams.get('uid') ?? '';

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  // Validate token on component mount
  useEffect(() => {
    if (!token) {
      setTokenValid(false);
      return;
    }

    // You can add token validation logic here
    // For now, we'll assume it's valid if present
    setTokenValid(true);
  }, [token]);

  const onSubmit = async (data: ResetPasswordFormData) => {
    if (!token) {
      toast.error(t('resetPassword.toastInvalidToken'));
      return;
    }

    try {
      await resetPassword(uid, token, data.password, data.confirmPassword);
      setResetComplete(true);
      toast.success(t('resetPassword.toastSuccess'));
    } catch (error: any) {
      toast.error(error?.detail || error?.message || t('resetPassword.toastError'));
    }
  };

  // Invalid token state
  if (tokenValid === false) {
    return (
      <div className="min-h-screen bg-gradient-medical dark:bg-gradient-medical-dark flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <Card variant="medical" className="animate-fade-in text-center">
            <CardContent className="pt-8">
              <div className="mx-auto w-16 h-16 bg-error-500 rounded-full flex items-center justify-center mb-6">
                <AlertCircle className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-error-600 dark:text-error-400 mb-4">
                {t('resetPassword.invalidTitle')}
              </h2>
              <p className="text-slate-600 dark:text-slate-400 mb-6">
                {t('resetPassword.invalidMessage')}
              </p>
              <div className="space-y-3">
                <Link to="/auth/forgot-password">
                  <Button variant="medical" fullWidth>
                    {t('resetPassword.requestNewLink')}
                  </Button>
                </Link>
                <Link to="/auth/login">
                  <Button variant="outline" fullWidth>
                    {t('forgotPassword.backToSignIn')}
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Success state
  if (resetComplete) {
    return (
      <div className="min-h-screen bg-gradient-medical dark:bg-gradient-medical-dark flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <Card variant="medical" className="animate-fade-in text-center">
            <CardContent className="pt-8">
              <div className="mx-auto w-16 h-16 bg-success-500 rounded-full flex items-center justify-center mb-6">
                <CheckCircle className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold medical-gradient-text mb-4">
                {t('resetPassword.successTitle')}
              </h2>
              <p className="text-slate-600 dark:text-slate-400 mb-6">
                {t('resetPassword.successMessage')}
              </p>
              <Button
                variant="medical"
                fullWidth
                onClick={() => navigate('/auth/login')}
              >
                {t('resetPassword.continueToSignIn')}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Loading state
  if (tokenValid === null) {
    return (
      <div className="min-h-screen bg-gradient-medical dark:bg-gradient-medical-dark flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <Card variant="medical" className="animate-fade-in">
            <CardContent className="py-12 text-center">
              <div className="animate-pulse-medical">
                <Stethoscope className="w-8 h-8 mx-auto text-medical-500 mb-4" />
                <p className="text-slate-600 dark:text-slate-400">{t('resetPassword.validating')}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-medical dark:bg-gradient-medical-dark flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div className="mx-auto w-16 h-16 bg-medical-500 rounded-full flex items-center justify-center mb-4">
            <Stethoscope className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold medical-gradient-text">{t('login.brand')}</h1>
        </div>

        <Card variant="medical" className="animate-fade-in">
          <CardHeader>
            <CardTitle className="text-center">{t('resetPassword.title')}</CardTitle>
            <p className="text-center text-slate-600 dark:text-slate-400 mt-2">
              {t('resetPassword.subtitle')}
            </p>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* Password Requirements */}
              <div className="p-4 rounded-medical bg-medical-50 dark:bg-medical-900/20 border border-medical-200 dark:border-medical-800">
                <h4 className="text-sm font-medium text-medical-800 dark:text-medical-200 mb-2">
                  {t('resetPassword.requirements')}
                </h4>
                <ul className="text-xs text-medical-700 dark:text-medical-300 space-y-1">
                  <li>• {t('resetPassword.req8chars')}</li>
                  <li>• {t('resetPassword.reqUppercase')}</li>
                  <li>• {t('resetPassword.reqLowercase')}</li>
                  <li>• {t('resetPassword.reqNumber')}</li>
                  <li>• {t('resetPassword.reqSpecial')}</li>
                </ul>
              </div>

              {/* New Password Input */}
              <div className="relative">
                <Input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  label={t('resetPassword.newPassword')}
                  leftIcon={Lock}
                  error={errors.password?.message}
                  placeholder="Enter your new password"
                  required
                  disabled={isSubmitting}
                  autoFocus
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
                  label={t('resetPassword.confirmPassword')}
                  leftIcon={Lock}
                  error={errors.confirmPassword?.message}
                  placeholder="Confirm your new password"
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

              {/* Submit Button */}
              <Button
                type="submit"
                variant="medical"
                size="lg"
                fullWidth
                loading={isSubmitting}
                leftIcon={Lock}
              >
                {isSubmitting ? t('resetPassword.submitting') : t('resetPassword.submit')}
              </Button>

              {/* Back to Login */}
              <div className="text-center">
                <Link
                  to="/auth/login"
                  className="text-sm text-medical-600 hover:text-medical-500 dark:text-medical-400 dark:hover:text-medical-300"
                >
                  {t('resetPassword.backToSignIn')}
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Security Notice */}
        <div className="mt-8 p-4 rounded-medical bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
          <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-2">
            {t('resetPassword.securityNotice')}
          </h4>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            {t('resetPassword.securityMessage')}
          </p>
        </div>
      </div>
    </div>
  );
};

export default ResetPasswordPage;