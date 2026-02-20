'use client';

import { useApp, THEMES } from '@/app/context';

export default function ThemeSelector() {
  const { theme, setTheme } = useApp();

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  return (
    <button
      onClick={toggleTheme}
      className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium transition-all"
      style={{ 
        background: 'var(--background-secondary)',
        color: 'var(--foreground-secondary)',
        borderRadius: 'var(--radius-sm)',
      }}
    >
      <span>{THEMES[theme].icon}</span>
      <span className="hidden sm:inline">{THEMES[theme].label}</span>
    </button>
  );
}
