import { apiClient } from "./client";
import { AuthResponse, User } from "@/types";

export const authApi = {
  register: async (data: { email: string; password: string; full_name?: string }): Promise<AuthResponse> => {
    const res = await apiClient.post<AuthResponse>("/auth/register", data);
    return res.data;
  },

  login: async (data: { email: string; password: string }): Promise<AuthResponse> => {
    const res = await apiClient.post<AuthResponse>("/auth/login", data);
    return res.data;
  },

  getMe: async (): Promise<User> => {
    const res = await apiClient.get<User>("/auth/me");
    return res.data;
  },
};
