import { apiClient } from '@shared/services/apiClient';

export interface AuditLogEntry {
  id: number;
  timestamp: string;
  username: string;
  action: string;
  table_name: string;
  record_id?: number | null;
  comments?: string | null;
}

export const auditApi = {
  async list(limit = 50): Promise<AuditLogEntry[]> {
    return (await apiClient.get<AuditLogEntry[]>('/audit-logs', { params: { limit } })).data;
  },
};
