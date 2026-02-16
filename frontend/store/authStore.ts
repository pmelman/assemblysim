import { create } from 'zustand';
import type { User } from '@/lib/types';
import { getMe } from '@/lib/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (token: string, user: User) => void;
  logout: () => void;
  setUser: (user: User) => void;
  loadFromStorage: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,

  login: (token, user) => {
    localStorage.setItem('auth_token', token);
    set({ token, user, isAuthenticated: true, isLoading: false });
  },

  logout: () => {
    localStorage.removeItem('auth_token');
    set({ token: null, user: null, isAuthenticated: false, isLoading: false });
  },

  setUser: (user) => {
    set({ user });
  },

  loadFromStorage: async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      set({ isLoading: false });
      return;
    }

    try {
      const user = await getMe();
      set({ token, user, isAuthenticated: true, isLoading: false });
    } catch {
      // Token is invalid or expired
      localStorage.removeItem('auth_token');
      set({ token: null, user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
