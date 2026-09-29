/**
 * Certificate of Analysis API calls.
 *
 * There is no update or delete — a certificate is issued once, and a correction
 * is a new certificate that supersedes it.
 */
import { apiClient } from '@shared/services/apiClient';
import type {
  COA,
  COASnapshot,
  COASummary,
  GenerateCOARequest,
  PreviewCOARequest,
} from '../models/coa.types';

export const coaApi = {
  async list(params?: { productId?: number; batchNumber?: string }): Promise<COASummary[]> {
    const query: Record<string, string | number> = {};
    if (params?.productId != null) query.product_id = params.productId;
    if (params?.batchNumber) query.batch_number = params.batchNumber;
    return (await apiClient.get<COASummary[]>('/coa', { params: query })).data;
  },

  async get(id: number): Promise<COA> {
    return (await apiClient.get<COA>(`/coa/${id}`)).data;
  },

  /** Compiles what a certificate would contain, without issuing one. */
  async preview(payload: PreviewCOARequest): Promise<COASnapshot> {
    const response = await apiClient.post<{ snapshot: COASnapshot }>('/coa/preview', payload);
    return response.data.snapshot;
  },

  async generate(payload: GenerateCOARequest): Promise<COA> {
    return (await apiClient.post<COA>('/coa', payload)).data;
  },
};
