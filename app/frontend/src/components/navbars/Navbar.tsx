import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Menu,
  X,
  Stethoscope,
  Moon,
  Sun,
  User,
  LogOut,
  Settings,
  Brain,
  FileText,
  Shield,
  Activity,
  BarChart3,
  ChevronDown,
  Globe,
  PawPrint,
  LayoutDashboard
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useTranslation } from 'react-i18next';

import { Button } from '../ui';
import { Dropdown, DropdownItem, DropdownDivider } from '../ui/Dropdown';
import { LanguageSelector } from '../settings/LanguageSelector';
import { NotificationBell } from '../notifications/NotificationBell';
import { NotificationDropdown } from '../notifications/NotificationDropdown';
import { useAuth, useTheme } from '../../contexts';
import { apiClient, type Notification } from '../../utils/api';
import { useWebSocket } from '../../hooks/useWebSocket';

const getRoleName = (role: number | undefined, t: (key: string) => string): string => {
  const map: Record<number, string> = {
    1: t('roles.user'),
    2: t('roles.guest'),
    3: t('roles.admin'),
    4: t('roles.manager'),
    5: t('roles.superuser'),
  };
  return map[role ?? 1] ?? t('roles.user');
};

const Navbar: React.FC = () => {
  const { t } = useTranslation('common');
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const { isAuthenticated, user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  const isAuthPage = location.pathname.startsWith('/auth');

  // Poll notifications every 30s
  const fetchNotifications = useCallback(async () => {
    try {
      const data = await apiClient.getNotifications();
      setNotifications(data);
    } catch {
      // Silently fail — user may not be authenticated yet
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated, fetchNotifications]);

  // Live notifications: prepend new ones as they arrive (deduped by id). The
  // 30s poll above remains a fallback if the socket is unavailable.
  const handleIncomingNotification = useCallback((m: any) => {
    if (m?.type !== 'notification_created' || !m.notification) return;
    setNotifications((prev) =>
      prev.some((n) => n.id === m.notification.id) ? prev : [m.notification, ...prev]
    );
  }, []);
  useWebSocket('/ws/notifications/', {
    autoConnect: isAuthenticated,
    onMessage: handleIncomingNotification,
  });

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkRead = async (id: number) => {
    try {
      await apiClient.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch { /* ignore */ }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiClient.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch { /* ignore */ }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const handleLogout = async () => {
    try {
      await logout();
      toast.success('Logged out successfully');
      navigate('/auth/login');
    } catch (error) {
      console.error('Logout error:', error);
      toast.error('Logout failed');
    } finally {
      setIsOpen(false);
    }
  };

  // Navigation items for non-authenticated users (home page)
  const publicNavigation = [
    { name: t('nav.models'), href: '/models', icon: Brain },
    { name: t('nav.documentation'), href: '/docs', icon: FileText },
    { name: t('nav.security'), href: '/security', icon: Shield },
  ];

  // Navigation items for authenticated users
  const authenticatedNavigation = [
    { name: t('nav.dashboard'), href: '/dashboard', icon: LayoutDashboard },
    { name: t('nav.patients'), href: '/patients', icon: PawPrint },
    { name: t('nav.analysis'), href: '/analyze', icon: FileText },
    { name: t('nav.statistics'), href: '/statistics', icon: BarChart3 },
    { name: t('nav.tools'), href: '/tools', icon: Settings },
    { name: t('nav.monitor'), href: '/monitor', icon: Activity },
    // Clinic admins / managers / superusers get the audit-log oversight view.
    ...((user?.role ?? 1) >= 3
      ? [{ name: t('nav.auditLog'), href: '/audit-log', icon: Shield }]
      : []),
  ];

  // Select navigation based on authentication status
  const navigation = isAuthenticated ? authenticatedNavigation : publicNavigation;

  // Helper function to check if a route is active
  const isActiveRoute = (href: string) => {
    if (href === '/models' && location.pathname === '/models') return true;
    return location.pathname.startsWith(href) && href !== '/';
  };


  if (isAuthPage) {
    // Minimal navbar for auth pages
    return (
      <nav className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <Link to="/" className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-medical-500 rounded-lg flex items-center justify-center">
                <Stethoscope className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold medical-gradient-text">VetImage</span>
            </Link>

            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label={t('theme.toggleTheme')}
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              ) : (
                <Moon className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              )}
            </button>
          </div>
        </div>
      </nav>
    );
  }

  return (
    <nav className="bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border-b border-slate-200 dark:border-slate-700 sticky top-0 z-40">
      <div className="max-w-8xl mx-auto">
        <div className="flex justify-between items-center py-4">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-medical-500 rounded-lg flex items-center justify-center">
              <Stethoscope className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold medical-gradient-text">VetImage</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = isActiveRoute(item.href);
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`
                    flex items-center space-x-1 px-3 py-2 rounded-lg font-medium transition-all
                    ${isActive
                      ? 'text-medical-600 dark:text-medical-400 bg-medical-50 dark:bg-medical-950/30 shadow-sm'
                      : 'text-slate-600 dark:text-slate-300 hover:text-medical-600 dark:hover:text-medical-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </div>

          {/* Desktop Auth Section */}
          <div className="hidden md:flex items-center space-x-4">
            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label={t('theme.toggleTheme')}
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              ) : (
                <Moon className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              )}
            </button>

            {/* Notification Bell */}
            {isAuthenticated && (
              <div className="relative" ref={notifRef}>
                <NotificationBell
                  unreadCount={unreadCount}
                  onClick={() => setShowNotifications(!showNotifications)}
                  isOpen={showNotifications}
                />
                {showNotifications && (
                  <NotificationDropdown
                    notifications={notifications}
                    onMarkRead={handleMarkRead}
                    onMarkAllRead={handleMarkAllRead}
                    onClose={() => setShowNotifications(false)}
                  />
                )}
              </div>
            )}

            {isAuthenticated ? (
              <Dropdown
                align="right"
                trigger={
                  <button className="flex items-center gap-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg px-3 py-2 transition-colors">
                    <div className="w-8 h-8 bg-medical-100 dark:bg-medical-900 rounded-full flex items-center justify-center overflow-hidden">
                      {user?.image_url ? (
                        <img
                          src={user.image_url}
                          alt="Avatar"
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <User className="w-4 h-4 text-medical-600 dark:text-medical-400" />
                      )}
                    </div>
                    <div className="hidden lg:block text-left">
                      <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                        {user?.email}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        {getRoleName(user?.role, t)}
                      </div>
                    </div>
                    <ChevronDown className="w-4 h-4 text-slate-600 dark:text-slate-400" />
                  </button>
                }
              >
                {/* User Info Header */}
                <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                  <div className="font-medium text-gray-900 dark:text-white">{user?.email}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {getRoleName(user?.role, t)}
                  </div>
                </div>

                <DropdownItem
                  icon={<User className="w-4 h-4" />}
                  label={t('userMenu.myProfile')}
                  href="/profile"
                />

                <DropdownDivider />

                {/* Language Selector */}
                <div className="px-2 py-1">
                  <div className="flex items-center gap-2 px-2 py-1 text-xs text-gray-500 dark:text-gray-400">
                    <Globe className="w-3 h-3" />
                    <span>{t('userMenu.language')}</span>
                  </div>
                  <LanguageSelector />
                </div>

                <DropdownDivider />

                {/* Logout */}
                <DropdownItem
                  icon={<LogOut className="w-4 h-4" />}
                  label={t('userMenu.logout')}
                  onClick={handleLogout}
                  danger
                />
              </Dropdown>
            ) : (
              <div className="flex items-center space-x-3">
                <Link to="/auth/login">
                  <Button variant="ghost" size="sm">
                    {t('nav.signIn')}
                  </Button>
                </Link>
                <Link to="/auth/register">
                  <Button variant="medical" size="sm">
                    {t('nav.getStarted')}
                  </Button>
                </Link>
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center space-x-2">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label={t('theme.toggleTheme')}
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              ) : (
                <Moon className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              )}
            </button>
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label="Toggle menu"
            >
              {isOpen ? (
                <X className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              ) : (
                <Menu className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isOpen && (
          <div className="md:hidden border-t border-slate-200 dark:border-slate-700 py-4">
            <div className="space-y-1 px-2">
              {/* Navigation Links */}
              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive = isActiveRoute(item.href);
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`
                      flex items-center space-x-3 px-4 py-2 rounded-lg font-medium transition-all
                      ${isActive
                        ? 'text-medical-600 dark:text-medical-400 bg-medical-50 dark:bg-medical-950/30 shadow-sm'
                        : 'text-slate-600 dark:text-slate-300 hover:text-medical-600 dark:hover:text-medical-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                      }
                    `}
                    onClick={() => setIsOpen(false)}
                  >
                    <Icon className="w-5 h-5" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}

              {isAuthenticated ? (
                <>
                  <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
                    {/* User Info */}
                    <div className="px-4 py-2 mb-4">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-medical-100 dark:bg-medical-900 rounded-full flex items-center justify-center overflow-hidden">
                          {user?.image_url ? (
                            <img
                              src={user.image_url}
                              alt="Avatar"
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <User className="w-5 h-5 text-medical-600 dark:text-medical-400" />
                          )}
                        </div>
                        <div>
                          <div className="font-medium text-slate-900 dark:text-slate-100">
                            {user?.email}
                          </div>
                          <div className="text-sm text-slate-500 dark:text-slate-400">
                            {getRoleName(user?.role, t)}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* User Navigation */}
                    <Link
                      to="/profile"
                      className={`
                        flex items-center space-x-3 px-4 py-2 rounded-lg font-medium transition-all
                        ${location.pathname === '/profile'
                          ? 'text-medical-600 dark:text-medical-400 bg-medical-50 dark:bg-medical-950/30 shadow-sm'
                          : 'text-slate-600 dark:text-slate-300 hover:text-medical-600 dark:hover:text-medical-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                        }
                      `}
                      onClick={() => setIsOpen(false)}
                    >
                      <User className="w-5 h-5" />
                      <span>{t('nav.profile')}</span>
                    </Link>

                    {/* Logout */}
                    <button
                      onClick={handleLogout}
                      className="flex items-center space-x-3 px-4 py-2 w-full text-left text-slate-600 dark:text-slate-300 hover:text-error-600 dark:hover:text-error-400 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg transition-colors"
                    >
                      <LogOut className="w-5 h-5" />
                      <span className="font-medium">{t('nav.signOut')}</span>
                    </button>
                  </div>
                </>
              ) : (
                <div className="border-t border-slate-200 dark:border-slate-700 pt-4 space-y-2 px-4">
                  <Link to="/auth/login" onClick={() => setIsOpen(false)}>
                    <Button variant="ghost" fullWidth>
                      {t('nav.signIn')}
                    </Button>
                  </Link>
                  <Link to="/auth/register" onClick={() => setIsOpen(false)}>
                    <Button variant="medical" fullWidth>
                      {t('nav.getStarted')}
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
