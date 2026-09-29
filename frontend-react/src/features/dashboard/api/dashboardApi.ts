import { apiClient } from '@shared/services/apiClient';
import type { DashboardStats } from '../models/dashboard.types';

export const dashboardApi = {
  async getStats(): Promise<DashboardStats> {
    const response = await apiClient.get<DashboardStats>('/dashboard');
    return response.data;
  },
};
