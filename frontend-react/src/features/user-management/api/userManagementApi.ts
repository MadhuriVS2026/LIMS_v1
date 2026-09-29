import { apiClient } from '@shared/services/apiClient';
import type { User } from '@features/authentication/models/auth.types';

export const userManagementApi = {
  async list(): Promise<User[]> {
    return (await apiClient.get<User[]>('/users')).data;
  },
  async create(payload: {
    username: string;
    password: string;
    full_name: string;
    role: string;
    email?: string;
    department?: string;
  }): Promise<User> {
    return (await apiClient.post<User>('/users', payload)).data;
  },
  async update(id: number, payload: Partial<User>): Promise<User> {
    return (await apiClient.put<User>(`/users/${id}`, payload)).data;
  },
};
