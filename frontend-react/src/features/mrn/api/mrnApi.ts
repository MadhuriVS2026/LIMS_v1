/**
 * MRN — Material Requisition & Consumption API calls.
 */
import { apiClient } from '@shared/services/apiClient';
import type {
  ApproveAndPostRequest,
  CreateLineItemRequest,
  MaterialQueuePullResponse,
  MaterialRequisition,
  MRNLineItem,
  MRNMaterialLot,
} from '../models/mrn.types';

export const mrnApi = {
  async getMaterialQueue(): Promise<MRNMaterialLot[]> {
    return (await apiClient.get<MRNMaterialLot[]>('/mrn/material-queue')).data;
  },
  async pullMaterialQueue(): Promise<MaterialQueuePullResponse> {
    return (await apiClient.post<MaterialQueuePullResponse>('/mrn/material-queue/pull')).data;
  },
  async list(): Promise<MaterialRequisition[]> {
    return (await apiClient.get<MaterialRequisition[]>('/mrn')).data;
  },
  async get(id: number): Promise<MaterialRequisition> {
    return (await apiClient.get<MaterialRequisition>(`/mrn/${id}`)).data;
  },
  async create(): Promise<MaterialRequisition> {
    return (await apiClient.post<MaterialRequisition>('/mrn')).data;
  },
  async addLineItem(mrnId: number, payload: CreateLineItemRequest): Promise<MRNLineItem> {
    return (await apiClient.post<MRNLineItem>(`/mrn/${mrnId}/line-items`, payload)).data;
  },
  async removeLineItem(mrnId: number, lineId: number): Promise<void> {
    await apiClient.delete(`/mrn/${mrnId}/line-items/${lineId}`);
  },
  async submit(mrnId: number): Promise<MaterialRequisition> {
    return (await apiClient.post<MaterialRequisition>(`/mrn/${mrnId}/submit`)).data;
  },
  async approveAndPost(mrnId: number, payload: ApproveAndPostRequest): Promise<MaterialRequisition> {
    return (await apiClient.post<MaterialRequisition>(`/mrn/${mrnId}/approve-post`, payload)).data;
  },
  async reprocess(mrnId: number): Promise<MaterialRequisition> {
    return (await apiClient.post<MaterialRequisition>(`/mrn/${mrnId}/reprocess`)).data;
  },
};
