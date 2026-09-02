/**
 * Management Page — Clinic Admins only.
 *
 * This is where a clinic decides who has access to its records. Personal
 * settings are not here: they already live under the account menu → My
 * Profile, and duplicating them would leave two forms writing the same fields.
 *
 * The route is gated on role 3 as well (App.tsx), and the backend refuses a
 * non-admin regardless — this page never assumes the client-side guard held.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { UserCog } from 'lucide-react';

import PageHeader from '../components/ui/PageHeader';
import { useAuth } from '../contexts';
import InvitationsSection from '../components/management/InvitationsSection';

const ManagementPage: React.FC = () => {
  const { t } = useTranslation('common');
  const { user } = useAuth();

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <PageHeader
        icon={UserCog}
        title={t('management.title')}
        subtitle={
          user?.clinic_name
            ? t('management.subtitleWithClinic', { clinic: user.clinic_name })
            : t('management.subtitle')
        }
      />
      <InvitationsSection />
    </div>
  );
};

export default ManagementPage;
