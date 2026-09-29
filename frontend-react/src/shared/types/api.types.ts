/**
 * Shared API-level types used across features.
 */
export interface ApiError {
  detail: string;
}

export interface ESignPayload {
  password: string;
  comments?: string;
}
