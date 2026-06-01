/**
 * Notification Bell
 *
 * Bell icon with unread badge for the navbar.
 * Toggles the notification dropdown on click.
 */

import React from 'react';
import { Bell } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface NotificationBellProps {
  unreadCount: number;
  onClick: () => void;
  isOpen: boolean;
}

export const NotificationBell: React.FC<NotificationBellProps> = ({
  unreadCount,
  onClick,
  isOpen,
}) => {
  const { t } = useTranslation('notifications');
  return (
    <button
      onClick={onClick}
      className={`relative p-2 rounded-lg transition-colors ${
        isOpen
          ? 'bg-medical-100 dark:bg-medical-900 text-medical-600 dark:text-medical-400'
          : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400'
      }`}
      aria-label={unreadCount > 0 ? t('ariaLabel', { count: unreadCount }) : t('title')}
    >
      <Bell className="w-5 h-5" />
      {unreadCount > 0 && (
        <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-error-500 rounded-full">
          {unreadCount > 99 ? '99+' : unreadCount}
        </span>
      )}
    </button>
  );
};

export default NotificationBell;
