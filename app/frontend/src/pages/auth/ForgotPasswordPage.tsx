import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Mail, Send, ArrowLeft, Stethoscope, CheckCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';

import { Button, Input, Card, CardHeader, CardTitle, CardContent } from '../../components/ui';
import { useAuth } from '../../contexts';
import { forgotPasswordSchema, ForgotPasswordFormData } from '../../utils/validation';

const ForgotPasswordPage: React.FC = () => {
  const { forgotPassword } = useAuth();
  const [emailSent, setEmailSent] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState('');
  const { t } = useTranslation('auth');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    try {
      await forgotPassword(data.email);
      setSubmittedEmail(data.email);
      setEmailSent(true);
      toast.success(t('forgotPassword.toastSuccess'));
    } catch (error: any) {
      toast.error(error?.detail || error?.message || t('forgotPassword.toastError'));
    }
  };

  if (emailSent) {
    return (
      <div className="min-h-screen bg-gradient-medical dark:bg-gradient-medical-dark flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <Card variant="medical" className="animate-fade-in text-center">
            <CardContent className="pt-8">
              <div className="mx-auto w-16 h-16 bg-medical-500 rounded-full flex items-center justify-center mb-6">
                <CheckCircle className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold medical-gradient-text mb-4">
                {t('forgotPassword.successTitle')}
              </h2>
              <p className="text-slate-600 dark:text-slate-400 mb-2">
                {t('forgotPassword.successMessage')}
              </p>
              <p className="font-medium text-slate-900 dark:text-slate-100 mb-6">
                {submittedEmail}
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                {t('forgotPassword.successInstruction')}
              </p>
              <div className="space-y-3">
                <Button
                  variant="medical"
                  fullWidth
                  onClick={() => window.location.href = 'mailto:'}
                >
                  {t('forgotPassword.openEmail')}
                </Button>
                <Button
                  variant="outline"
                  fullWidth
                  onClick={() => setEmailSent(false)}
                >
                  {t('forgotPassword.tryAnotherEmail')}
                </Button>
                <Link to="/auth/login">
                  <Button variant="ghost" fullWidth>
                    {t('forgotPassword.backToSignIn')}
                  </Button>
                </Link>
              </div>
              <div className="mt-8 text-xs text-slate-500 dark:text-slate-400">
                <p>{t('forgotPassword.didntReceive')}</p>
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
            <CardTitle className="text-center">{t('forgotPassword.title')}</CardTitle>
            <p className="text-center text-slate-600 dark:text-slate-400 mt-2">
              {t('forgotPassword.subtitle')}
            </p>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* Email Input */}
              <Input
                {...register('email')}
                type="email"
                label={t('forgotPassword.email')}
                leftIcon={Mail}
                error={errors.email?.message}
                placeholder="vet@clinic.com"
                helper={t('forgotPassword.emailHelp')}
                required
                disabled={isSubmitting}
                autoFocus
              />

              {/* Submit Button */}
              <Button
                type="submit"
                variant="medical"
                size="lg"
                fullWidth
                loading={isSubmitting}
                leftIcon={Send}
              >
                {isSubmitting ? t('forgotPassword.submitting') : t('forgotPassword.submit')}
              </Button>

              {/* Back to Login */}
              <div className="text-center">
                <Link
                  to="/auth/login"
                  className="inline-flex items-center text-sm text-medical-600 hover:text-medical-500 dark:text-medical-400 dark:hover:text-medical-300"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  {t('forgotPassword.backToSignIn')}
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Security Notice */}
        <div className="mt-8 p-4 rounded-medical bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
          <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-2">
            {t('forgotPassword.securityNotice')}
          </h4>
          <ul className="text-xs text-slate-600 dark:text-slate-400 space-y-1">
            <li>• {t('forgotPassword.securityTip1')}</li>
            <li>• {t('forgotPassword.securityTip2')}</li>
            <li>• {t('forgotPassword.securityTip3')}</li>
          </ul>
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-sm text-slate-500 dark:text-slate-400">
          <p>
            {t('forgotPassword.needHelp')}{' '}
            <Link
              to="/support"
              className="text-medical-600 hover:text-medical-500 dark:text-medical-400 dark:hover:text-medical-300"
            >
              {t('forgotPassword.contactSupport')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;