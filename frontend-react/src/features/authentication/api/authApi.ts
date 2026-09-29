/**
 * Authentication API calls.
 */
import { apiClient } from '@shared/services/apiClient';
import type { LoginCredentials, PasswordChangeRequest, TokenResponse, User } from '../models/auth.types';

export const authApi = {
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    const response = await apiClient.post<TokenResponse>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },

  async getMe(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },

  async changePassword(request: PasswordChangeRequest): Promise<void> {
    await apiClient.post('/auth/change-password', request);
  },
};
