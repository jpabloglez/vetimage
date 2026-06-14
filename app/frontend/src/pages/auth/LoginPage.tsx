import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Mail, Lock, Eye, EyeOff, LogIn, Stethoscope } from 'lucide-react';
import { toast } from 'react-hot-toast';

import { Button, Input, Card, CardHeader, CardTitle, CardContent } from '../../components/ui';
import { useAuth } from '../../contexts';
import { loginSchema, LoginFormData } from '../../utils/validation';

const LoginPage: React.FC = () => {
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const { t } = useTranslation('auth');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  // Friendly notice when redirected here by an expired session.
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('session') === 'expired') {
      toast.error(t('login.sessionExpired', 'Your session expired. Please sign in again.'));
    }
  }, [t]);

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login(data.email, data.password);
      toast.success(t('login.toastSuccess'));
      navigate('/models');
    } catch (error: any) {
      console.error('Login error:', error);
      toast.error(error.message || t('login.toastError'));
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
            <CardTitle className="text-center">{t('login.title')}</CardTitle>
            <p className="text-center text-slate-600 dark:text-slate-400 mt-2">
              {t('login.subtitle')}
            </p>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* Email Input */}
              <Input
                {...register('email')}
                type="email"
                label={t('login.email')}
                leftIcon={Mail}
                error={errors.email?.message}
                placeholder="vet@clinic.com"
                required
                disabled={isSubmitting}
              />

              {/* Password Input */}
              <div className="relative">
                <Input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  label={t('login.password')}
                  leftIcon={Lock}
                  error={errors.password?.message}
                  placeholder="Enter your password"
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

              {/* Remember Me & Forgot Password */}
              <div className="flex items-center justify-between">
                <label className="flex items-center">
                  <input
                    {...register('rememberMe')}
                    type="checkbox"
                    className="rounded border-slate-300 text-medical-500 focus:ring-medical-500"
                    disabled={isSubmitting}
                  />
                  <span className="ml-2 text-sm text-slate-600 dark:text-slate-400">
                    {t('login.rememberMe')}
                  </span>
                </label>

                <Link
                  to="/auth/forgot-password"
                  className="text-sm text-medical-600 hover:text-medical-500 dark:text-medical-400 dark:hover:text-medical-300"
                >
                  {t('login.forgotPassword')}
                </Link>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="medical"
                size="lg"
                fullWidth
                loading={isSubmitting || isLoading}
                leftIcon={LogIn}
              >
                {isSubmitting || isLoading ? t('login.submitting') : t('login.submit')}
              </Button>

              {/* Sign Up Link */}
              <div className="text-center">
                <span className="text-slate-600 dark:text-slate-400">
                  {t('login.noAccount')}{' '}
                  <Link
                    to="/auth/register"
                    className="text-medical-600 hover:text-medical-500 dark:text-medical-400 dark:hover:text-medical-300 font-medium"
                  >
                    {t('login.signUp')}
                  </Link>
                </span>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center mt-8 text-sm text-slate-500 dark:text-slate-400">
          <p>{t('login.copyright', { year: new Date().getFullYear() })}</p>
          <div className="flex justify-center space-x-4 mt-2">
            <Link to="/privacy" className="hover:text-medical-500">{t('login.privacy')}</Link>
            <Link to="/terms" className="hover:text-medical-500">{t('login.terms')}</Link>
            <Link to="/support" className="hover:text-medical-500">{t('login.support')}</Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;