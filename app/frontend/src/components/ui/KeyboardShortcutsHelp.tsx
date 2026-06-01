/**
 * Keyboard Shortcuts Help Modal
 *
 * Shows available keyboard shortcuts. Triggered by pressing '?'.
 */

import React from 'react';
import { X, Keyboard } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { ShortcutDef } from '../../hooks/useKeyboardShortcuts';

interface KeyboardShortcutsHelpProps {
  isOpen: boolean;
  onClose: () => void;
  shortcuts: ShortcutDef[];
}

export const KeyboardShortcutsHelp: React.FC<KeyboardShortcutsHelpProps> = ({
  isOpen,
  onClose,
  shortcuts,
}) => {
  const { t } = useTranslation('common');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2">
            <Keyboard className="w-5 h-5 text-medical-500" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              {t('shortcuts.title')}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {/* Shortcuts List */}
        <div className="px-6 py-4 space-y-3 max-h-80 overflow-y-auto">
          {shortcuts.map((shortcut) => (
            <div
              key={shortcut.key}
              className="flex items-center justify-between"
            >
              <span className="text-sm text-slate-700 dark:text-slate-300">
                {shortcut.description}
              </span>
              <kbd className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-mono font-semibold bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-600">
                {shortcut.ctrl && <span className="mr-1">Ctrl+</span>}
                {shortcut.label}
              </kbd>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-700">
          <p className="text-xs text-slate-500 dark:text-slate-400 text-center">
            {t('shortcuts.pressEscToClose')}
          </p>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcutsHelp;
