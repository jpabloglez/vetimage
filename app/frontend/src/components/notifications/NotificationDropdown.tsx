/**
 * Notification Dropdown
 *
 * Dropdown panel showing recent notifications with mark-read actions.
 */

import React from 'react';
import { CheckCheck, Info, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import type { Notification } from '../../utils/api';

interface NotificationDropdownProps {
  notifications: Notification[];
  onMarkRead: (id: number) => void;
  onMarkAllRead: () => void;
  onClose: () => void;
}

const typeConfig = {
  info: { icon: Info, color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20' },
  success: { icon: CheckCircle, color: 'text-success-500', bg: 'bg-success-50 dark:bg-success-900/20' },
  warning: { icon: AlertTriangle, color: 'text-amber-500', bg: 'bg-amber-50 dark:bg-amber-900/20' },
  error: { icon: XCircle, color: 'text-error-500', bg: 'bg-error-50 dark:bg-error-900/20' },
};

function timeAgo(dateStr: string, t: (key: string, options?: Record<string, unknown>) => string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return t('common:time.justNow');
  if (minutes < 60) return t('common:time.minutesAgo', { count: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t('common:time.hoursAgo', { count: hours });
  const days = Math.floor(hours / 24);
  return t('common:time.daysAgo', { count: days });
}

export const NotificationDropdown: React.FC<NotificationDropdownProps> = ({
  notifications,
  onMarkRead,
  onMarkAllRead,
  onClose,
}) => {
  const { t } = useTranslation('notifications');
  const navigate = useNavigate();
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const handleClick = (notification: Notification) => {
    if (!notification.is_read) {
      onMarkRead(notification.id);
    }
    if (notification.link) {
      navigate(notification.link);
      onClose();
    }
  };

  return (
    <div className="absolute right-0 top-full mt-2 w-80 sm:w-96 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 z-50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
          {t('title')}
        </h3>
        {unreadCount > 0 && (
          <button
            onClick={onMarkAllRead}
            className="flex items-center gap-1 text-xs text-medical-600 dark:text-medical-400 hover:text-medical-700 dark:hover:text-medical-300 transition-colors"
          >
            <CheckCheck className="w-3.5 h-3.5" />
            {t('markAllRead')}
          </button>
        )}
      </div>

      {/* Notifications List */}
      <div className="max-h-80 overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-slate-500 dark:text-slate-400">
            {t('noNotifications')}
          </div>
        ) : (
          notifications.map((notification) => {
            const config = typeConfig[notification.notification_type] || typeConfig.info;
            const Icon = config.icon;

            return (
              <button
                key={notification.id}
                onClick={() => handleClick(notification)}
                className={`w-full text-left px-4 py-3 flex gap-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors border-b border-slate-100 dark:border-slate-700/50 last:border-0 ${
                  !notification.is_read ? 'bg-medical-50/50 dark:bg-medical-900/10' : ''
                }`}
              >
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${config.bg}`}>
                  <Icon className={`w-4 h-4 ${config.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm ${!notification.is_read ? 'font-medium text-slate-900 dark:text-white' : 'text-slate-600 dark:text-slate-400'}`}>
                    {notification.message}
                  </p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                    {timeAgo(notification.created_at, t)}
                  </p>
                </div>
                {!notification.is_read && (
                  <div className="flex-shrink-0 w-2 h-2 rounded-full bg-medical-500 mt-2" />
                )}
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};

export default NotificationDropdown;
