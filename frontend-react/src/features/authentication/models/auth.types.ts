/**
 * Authentication domain types.
 */
export interface User {
  id: number;
  username: string;
  full_name: string;
  role: 'Admin' | 'Analyst' | 'Supervisor' | 'QA' | 'GL' | 'TL' | 'Scientist' | 'FDGL' | 'ADGL' | 'Approver2';
  email?: string | null;
  department?: string | null;
  is_active: boolean;
  created_date?: string | null;
  last_login?: string | null;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}
