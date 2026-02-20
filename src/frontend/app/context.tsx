'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from '@/lib/api';

/* 主题类型：浅色或深色 */
export type ThemeType = 'light' | 'dark';

/* 主题配置 */
export const THEMES: Record<ThemeType, { label: string; icon: string }> = {
  light: { label: '浅色', icon: '☀️' },
  dark: { label: '深色', icon: '🌙' },
};

interface AppContextType {
  user: User | null;
  setUser: (user: User | null) => void;
  createUser: (nickname?: string) => Promise<User>;
  logout: () => void;
  loadUser: () => void;
  theme: ThemeType;
  setTheme: (theme: ThemeType) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [theme, setThemeState] = useState<ThemeType>('light');

  /* 初始化时从localStorage加载主题 */
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as ThemeType | null;
    if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
      setThemeState(savedTheme);
      document.documentElement.setAttribute('data-theme', savedTheme);
      if (savedTheme === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
  }, []);

  /* 切换主题 */
  const setTheme = (newTheme: ThemeType) => {
    setThemeState(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  const loadUser = () => {
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/users/${savedUserId}`)
        .then(res => res.json())
        .then(data => setUser(data))
        .catch(err => console.error('Failed to load user:', err));
    }
  };

  const createUser = async (nickname?: string) => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/users/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname }),
      });
      const data: User = await res.json();
      localStorage.setItem('userId', data.id);
      setUser(data);
      return data;
    } catch (error) {
      console.error('Failed to create user:', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('userId');
    setUser(null);
  };

  return (
    <AppContext.Provider value={{ user, setUser, createUser, logout, loadUser, theme, setTheme }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
}
