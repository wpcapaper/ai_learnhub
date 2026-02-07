'use client';

import { createContext, useContext, useState, ReactNode } from 'react';
import { User, Question } from '@/lib/api';

interface AppContextType {
  user: User | null;
  setUser: (user: User | null) => void;
  createUser: (nickname?: string) => Promise<User>;
  logout: () => void;
  loadUser: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

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
      const savedUserId = localStorage.getItem('userId');
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
    <AppContext.Provider value={{ user, setUser, createUser, logout, loadUser }}>
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
