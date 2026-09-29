/**
 * Worksheet API calls.
 *
 * A worksheet is created and found through its TRF test line, then addressed by
 * its own id, which is why the paths here span two prefixes.
 */
import { apiClient } from '@shared/services/apiClient';
import type {
  ConfirmWorksheetResponse,
  CreateWorksheetRequest,
  SaveWorksheetRequest,
  Worksheet,
  WorksheetComputed,
  WorksheetDetail,
  WorksheetValuesRequest,
} from '../models/testTemplate.types';

export const worksheetApi = {
  async createForLine(lineId: number, payload: CreateWorksheetRequest): Promise<WorksheetDetail> {
    return (
      await apiClient.post<WorksheetDetail>(`/trf/test-lines/${lineId}/worksheet`, payload)
    ).data;
  },
  /**
   * Resolves to `null` when the line has no worksheet. The backend returns 404
   * for that case, which is a normal state (not every test is templated) rather
   * than an error the caller should have to catch.
   */
  async getForLine(lineId: number): Promise<WorksheetDetail | null> {
    try {
      return (await apiClient.get<WorksheetDetail>(`/trf/test-lines/${lineId}/worksheet`)).data;
    } catch (error) {
      const status = (error as { response?: { status?: number } }).response?.status;
      if (status === 404) return null;
      throw error;
    }
  },
  async get(worksheetId: number): Promise<WorksheetDetail> {
    return (await apiClient.get<WorksheetDetail>(`/worksheets/${worksheetId}`)).data;
  },
  async listForTrf(trfId: number): Promise<Worksheet[]> {
    return (await apiClient.get<Worksheet[]>(`/trf/${trfId}/worksheets`)).data;
  },
  /** Recalculates against candidate values without persisting anything. */
  async preview(worksheetId: number, payload: WorksheetValuesRequest): Promise<WorksheetComputed> {
    return (await apiClient.post<WorksheetComputed>(`/worksheets/${worksheetId}/preview`, payload))
      .data;
  },
  async saveValues(worksheetId: number, payload: SaveWorksheetRequest): Promise<WorksheetDetail> {
    return (await apiClient.put<WorksheetDetail>(`/worksheets/${worksheetId}/values`, payload)).data;
  },
  async confirm(worksheetId: number): Promise<ConfirmWorksheetResponse> {
    return (await apiClient.post<ConfirmWorksheetResponse>(`/worksheets/${worksheetId}/confirm`))
      .data;
  },
};
