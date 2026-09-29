import { apiClient } from '@shared/services/apiClient';
import type { OOSInvestigation } from '../models/oos.types';

export const oosApi = {
  async list(): Promise<OOSInvestigation[]> {
    return (await apiClient.get<OOSInvestigation[]>('/oos')).data;
  },
  async close(id: number, rootCause: string, correctiveAction: string, password: string): Promise<OOSInvestigation> {
    return (
      await apiClient.post<OOSInvestigation>(`/oos/${id}/close`, {
        root_cause: rootCause,
        corrective_action: correctiveAction,
        password,
      })
    ).data;
  },
};
