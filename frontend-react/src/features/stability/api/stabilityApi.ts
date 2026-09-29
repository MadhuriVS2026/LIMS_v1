/**
 * Stability Management API calls.
 */
import { apiClient } from '@shared/services/apiClient';
import type {
  CancelProtocolRequest,
  CreateProtocolRequest,
  CreateReservePullRequest,
  EsignActionRequest,
  GenerateScheduleRequest,
  MatrixCellInput,
  SetReportSignatureNamesRequest,
  StabilityMatrixCell,
  StabilityProtocol,
  StabilityReport,
  StabilitySample,
  UpdateProtocolHeaderRequest,
} from '../models/stability.types';

export const stabilityApi = {
  // ── Protocols ──
  async listProtocols(): Promise<StabilityProtocol[]> {
    return (await apiClient.get<StabilityProtocol[]>('/stability/protocols')).data;
  },
  async getProtocol(id: number): Promise<StabilityProtocol> {
    return (await apiClient.get<StabilityProtocol>(`/stability/protocols/${id}`)).data;
  },
  async createProtocol(payload: CreateProtocolRequest): Promise<StabilityProtocol> {
    return (await apiClient.post<StabilityProtocol>('/stability/protocols', payload)).data;
  },
  async updateProtocolHeader(id: number, payload: UpdateProtocolHeaderRequest): Promise<StabilityProtocol> {
    return (await apiClient.patch<StabilityProtocol>(`/stability/protocols/${id}`, payload)).data;
  },
  async completeProtocol(id: number): Promise<StabilityProtocol> {
    return (await apiClient.post<StabilityProtocol>(`/stability/protocols/${id}/complete`)).data;
  },
  async cancelProtocol(id: number, payload: CancelProtocolRequest): Promise<StabilityProtocol> {
    return (await apiClient.post<StabilityProtocol>(`/stability/protocols/${id}/cancel`, payload)).data;
  },

  // ── Loading Matrix ──
  async getMatrix(protocolId: number): Promise<StabilityMatrixCell[]> {
    return (await apiClient.get<StabilityMatrixCell[]>(`/stability/protocols/${protocolId}/matrix`)).data;
  },
  async setMatrix(protocolId: number, cells: MatrixCellInput[]): Promise<StabilityMatrixCell[]> {
    return (
      await apiClient.put<StabilityMatrixCell[]>(`/stability/protocols/${protocolId}/matrix`, { cells })
    ).data;
  },

  // ── Two-step approval ──
  async checkFormulation(protocolId: number, payload: EsignActionRequest): Promise<StabilityProtocol> {
    return (
      await apiClient.post<StabilityProtocol>(`/stability/protocols/${protocolId}/check-formulation`, payload)
    ).data;
  },
  async checkAnalytical(protocolId: number, payload: EsignActionRequest): Promise<StabilityProtocol> {
    return (
      await apiClient.post<StabilityProtocol>(`/stability/protocols/${protocolId}/check-analytical`, payload)
    ).data;
  },

  // ── Schedule & pull ──
  async generateSchedule(protocolId: number, payload: GenerateScheduleRequest): Promise<StabilitySample[]> {
    return (
      await apiClient.post<StabilitySample[]>(`/stability/protocols/${protocolId}/generate-schedule`, payload)
    ).data;
  },
  async listSamples(protocolId: number): Promise<StabilitySample[]> {
    return (await apiClient.get<StabilitySample[]>(`/stability/protocols/${protocolId}/samples`)).data;
  },
  async pullSample(stabilitySampleId: number): Promise<StabilitySample> {
    return (await apiClient.post<StabilitySample>(`/stability/samples/${stabilitySampleId}/pull`)).data;
  },
  async createReservePull(protocolId: number, payload: CreateReservePullRequest): Promise<StabilitySample> {
    return (
      await apiClient.post<StabilitySample>(`/stability/protocols/${protocolId}/reserve-pull`, payload)
    ).data;
  },

  // ── Reports ──
  async generateReport(protocolId: number): Promise<StabilityReport> {
    return (await apiClient.post<StabilityReport>(`/stability/protocols/${protocolId}/reports`)).data;
  },
  async listReports(protocolId: number): Promise<StabilityReport[]> {
    return (await apiClient.get<StabilityReport[]>(`/stability/protocols/${protocolId}/reports`)).data;
  },
  async getReport(reportId: number): Promise<StabilityReport> {
    return (await apiClient.get<StabilityReport>(`/stability/reports/${reportId}`)).data;
  },
  async setReportSignatureNames(reportId: number, payload: SetReportSignatureNamesRequest): Promise<StabilityReport> {
    return (
      await apiClient.patch<StabilityReport>(`/stability/reports/${reportId}/signature-names`, payload)
    ).data;
  },
  async prepareReport(reportId: number, payload: EsignActionRequest): Promise<StabilityReport> {
    return (await apiClient.post<StabilityReport>(`/stability/reports/${reportId}/prepare`, payload)).data;
  },
  async approveReport(reportId: number, payload: EsignActionRequest): Promise<StabilityReport> {
    return (await apiClient.post<StabilityReport>(`/stability/reports/${reportId}/approve`, payload)).data;
  },
};
