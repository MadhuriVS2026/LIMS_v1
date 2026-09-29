/**
 * TRF — Test Request Form API calls.
 */
import { apiClient } from '@shared/services/apiClient';
import type {
  ATRResponse,
  CreateTestLineRequest,
  CreateTRFRequest,
  EsignActionRequest,
  ReferBackRejectRequest,
  SubmitTestResultRequest,
  TestRequestForm,
  TRFTestLine,
} from '../models/trf.types';

export const trfApi = {
  async create(payload: CreateTRFRequest): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>('/trf', payload)).data;
  },
  async list(): Promise<TestRequestForm[]> {
    return (await apiClient.get<TestRequestForm[]>('/trf')).data;
  },
  async get(id: number): Promise<TestRequestForm> {
    return (await apiClient.get<TestRequestForm>(`/trf/${id}`)).data;
  },
  async getATR(id: number): Promise<ATRResponse> {
    return (await apiClient.get<ATRResponse>(`/trf/${id}/atr`)).data;
  },
  async addTestLine(trfId: number, payload: CreateTestLineRequest): Promise<TRFTestLine> {
    return (await apiClient.post<TRFTestLine>(`/trf/${trfId}/test-lines`, payload)).data;
  },
  async removeTestLine(trfId: number, lineId: number): Promise<void> {
    await apiClient.delete(`/trf/${trfId}/test-lines/${lineId}`);
  },
  async submit(trfId: number): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/submit`)).data;
  },
  async fdglApprove(trfId: number, payload: EsignActionRequest): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/fdgl-approve`, payload)).data;
  },
  async fdglReferBack(trfId: number, payload: ReferBackRejectRequest): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/fdgl-refer-back`, payload)).data;
  },
  async fdglReject(trfId: number, payload: ReferBackRejectRequest): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/fdgl-reject`, payload)).data;
  },
  async adglAccept(trfId: number, payload: EsignActionRequest): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/adgl-accept`, payload)).data;
  },
  async adglReferBack(trfId: number, payload: ReferBackRejectRequest): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/adgl-refer-back`, payload)).data;
  },
  async adglReject(trfId: number, payload: ReferBackRejectRequest): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/adgl-reject`, payload)).data;
  },
  async analystAccept(trfId: number): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/analyst-accept`)).data;
  },
  async analystReferBack(trfId: number, payload: ReferBackRejectRequest): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/analyst-refer-back`, payload)).data;
  },
  async analystReject(trfId: number, payload: ReferBackRejectRequest): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/analyst-reject`, payload)).data;
  },
  async submitTestResult(lineId: number, payload: SubmitTestResultRequest): Promise<TRFTestLine> {
    return (await apiClient.put<TRFTestLine>(`/trf/test-lines/${lineId}/result`, payload)).data;
  },
  async submitResults(trfId: number, payload: EsignActionRequest): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/submit-results`, payload)).data;
  },
  async release(trfId: number, payload: EsignActionRequest): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/release`, payload)).data;
  },
  async resubmit(trfId: number): Promise<TestRequestForm> {
    return (await apiClient.post<TestRequestForm>(`/trf/${trfId}/resubmit`)).data;
  },
};
