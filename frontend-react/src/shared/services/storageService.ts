/**
 * Local storage wrapper for JWT token persistence.
 */
const ACCESS_TOKEN_KEY = 'lims_access_token';

export const storageService = {
  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },
  setAccessToken(token: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  },
  clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  },
};
