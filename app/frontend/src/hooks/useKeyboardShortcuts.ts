/**
 * Global Keyboard Shortcuts Hook
 *
 * Provides app-wide keyboard shortcuts for navigation and actions.
 * Shortcuts are disabled when focus is in input/textarea elements.
 */

import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

export interface ShortcutDef {
  key: string;
  label: string;
  description: string;
  action: () => void;
  ctrl?: boolean;
  shift?: boolean;
}

function isInputFocused(): boolean {
  const active = document.activeElement;
  if (!active) return false;
  const tag = active.tagName.toLowerCase();
  return tag === 'input' || tag === 'textarea' || tag === 'select' || (active as HTMLElement).isContentEditable;
}

export function useKeyboardShortcuts(
  onOpenHelp: () => void,
  extraShortcuts: ShortcutDef[] = [],
) {
  const navigate = useNavigate();

  const shortcuts: ShortcutDef[] = [
    { key: '?', label: '?', description: 'Show keyboard shortcuts', action: onOpenHelp, shift: true },
    { key: 'u', label: 'U', description: 'Go to Upload / Analyze', action: () => navigate('/analyze') },
    { key: 'm', label: 'M', description: 'Go to Models', action: () => navigate('/models') },
    { key: 's', label: 'S', description: 'Go to Statistics', action: () => navigate('/statistics') },
    { key: 'o', label: 'O', description: 'Go to Monitor', action: () => navigate('/monitor') },
    ...extraShortcuts,
  ];

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (isInputFocused()) return;

      for (const shortcut of shortcuts) {
        const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase() ||
          (shortcut.key === '?' && e.key === '?');
        const ctrlMatch = shortcut.ctrl ? (e.ctrlKey || e.metaKey) : !(e.ctrlKey || e.metaKey);
        const shiftMatch = shortcut.shift ? e.shiftKey : true; // shift is optional unless required

        if (keyMatch && ctrlMatch) {
          e.preventDefault();
          shortcut.action();
          return;
        }
      }
    },
    [shortcuts],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return shortcuts;
}

export default useKeyboardShortcuts;
