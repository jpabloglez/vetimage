/**
 * Management Page — Clinic Admins only.
 *
 * This is where a clinic decides who has access to its records: the staff
 * roster, invitations, and the clinic's own details. Personal settings are not
 * here — they live under the account menu → My Profile, and duplicating them
 * would leave two forms writing the same fields.
 *
 * The route is gated on role 3 as well (App.tsx), and the backend refuses a
 * non-admin regardless — this page never assumes the client-side guard held.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { UserCog } from 'lucide-react';

import PageHeader from '../components/ui/PageHeader';
import { useAuth } from '../contexts';
import MembersSection from '../components/management/MembersSection';
import InvitationsSection from '../components/management/InvitationsSection';
import ClinicProfileSection from '../components/management/ClinicProfileSection';

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
      <div className="space-y-6">
        {/* Roster first: who is already here is the question an admin arrives
            with. Inviting follows, then the clinic's own details. */}
        <MembersSection />
        <InvitationsSection />
        <ClinicProfileSection />
      </div>
    </div>
  );
};

export default ManagementPage;
