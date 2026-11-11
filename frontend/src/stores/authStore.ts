import { create } from "zustand";
import { User } from "@/types";

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
}

const TOKEN_KEY = "finsight_auth_token";
const USER_KEY = "finsight_auth_user";

export const useAuthStore = create<AuthState>((set) => {
  const savedToken = localStorage.getItem(TOKEN_KEY);
  const savedUser = localStorage.getItem(USER_KEY);

  let initialUser: User | null = null;
  if (savedUser) {
    try {
      initialUser = JSON.parse(savedUser);
    } catch {
      localStorage.removeItem(USER_KEY);
    }
  }

  return {
    token: savedToken,
    user: initialUser,
    isAuthenticated: !!savedToken,
    setAuth: (token: string, user: User) => {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      set({ token, user, isAuthenticated: true });
    },
    logout: () => {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      set({ token: null, user: null, isAuthenticated: false });
    },
  };
});
