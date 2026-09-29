/**
 * Resource Manager API calls.
 */
import { apiClient } from '@shared/services/apiClient';
import type {
  ChemicalReagent,
  ColumnMaster,
  Instrument,
  ReferenceStandard,
  VolumetricSolution,
} from '../models/resource.types';

export const instrumentApi = {
  async list(): Promise<Instrument[]> {
    return (await apiClient.get<Instrument[]>('/instruments')).data;
  },
  async create(payload: Partial<Instrument>): Promise<Instrument> {
    return (await apiClient.post<Instrument>('/instruments', payload)).data;
  },
  async calibrate(id: number, payload: Record<string, unknown>): Promise<Instrument> {
    return (await apiClient.post<Instrument>(`/instruments/${id}/calibrate`, payload)).data;
  },
};

export const columnApi = {
  async list(): Promise<ColumnMaster[]> {
    return (await apiClient.get<ColumnMaster[]>('/columns')).data;
  },
  async create(payload: Partial<ColumnMaster>): Promise<ColumnMaster> {
    return (await apiClient.post<ColumnMaster>('/columns', payload)).data;
  },
};

export const referenceStandardApi = {
  async list(): Promise<ReferenceStandard[]> {
    return (await apiClient.get<ReferenceStandard[]>('/reference-standards')).data;
  },
  async create(payload: Partial<ReferenceStandard>): Promise<ReferenceStandard> {
    return (await apiClient.post<ReferenceStandard>('/reference-standards', payload)).data;
  },
};

export const chemicalApi = {
  async list(): Promise<ChemicalReagent[]> {
    return (await apiClient.get<ChemicalReagent[]>('/chemicals')).data;
  },
  async create(payload: Partial<ChemicalReagent>): Promise<ChemicalReagent> {
    return (await apiClient.post<ChemicalReagent>('/chemicals', payload)).data;
  },
};

export const volumetricApi = {
  async list(): Promise<VolumetricSolution[]> {
    return (await apiClient.get<VolumetricSolution[]>('/volumetric-solutions')).data;
  },
  async create(payload: Partial<VolumetricSolution>): Promise<VolumetricSolution> {
    return (await apiClient.post<VolumetricSolution>('/volumetric-solutions', payload)).data;
  },
};

// Stability now has its own dedicated feature — see @features/stability/api/stabilityApi.ts
