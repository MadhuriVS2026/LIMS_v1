import { apiClient } from '@shared/services/apiClient';
import type { SAPIntegrationLog, SAPReceivedLot, SAPUsageDecisionResponse } from '../models/sap.types';

export const sapApi = {
  async postUsageDecision(payload: {
    sample_id: number;
    ud_code: string;
    password: string;
  }): Promise<SAPUsageDecisionResponse> {
    return (await apiClient.post<SAPUsageDecisionResponse>('/sap/usage-decision', payload)).data;
  },
  async getLogs(): Promise<SAPIntegrationLog[]> {
    return (await apiClient.get<SAPIntegrationLog[]>('/sap/logs')).data;
  },
  async getReceivedLots(): Promise<SAPReceivedLot[]> {
    return (await apiClient.get<SAPReceivedLot[]>('/sap/inbound/inspection-lot')).data;
  },
};
