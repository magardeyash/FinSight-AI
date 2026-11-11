import { apiClient } from "./client";
import { DashboardStats, RecentActivity } from "@/types";

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const res = await apiClient.get<DashboardStats>("/dashboard/stats");
    return res.data;
  },

  getRecentActivity: async (): Promise<RecentActivity[]> => {
    const res = await apiClient.get<RecentActivity[]>("/dashboard/recent-activity");
    return res.data;
  },
};
