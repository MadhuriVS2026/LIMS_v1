/**
 * TanStack Query hooks for the Resource Manager feature.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  chemicalApi,
  columnApi,
  instrumentApi,
  referenceStandardApi,
  volumetricApi,
} from '../api/resourceApi';

export function useInstruments() {
  return useQuery({ queryKey: ['instruments'], queryFn: instrumentApi.list });
}
export function useCreateInstrument() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: instrumentApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['instruments'] }) });
}

export function useColumns() {
  return useQuery({ queryKey: ['columns'], queryFn: columnApi.list });
}
export function useCreateColumn() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: columnApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['columns'] }) });
}

export function useReferenceStandards() {
  return useQuery({ queryKey: ['reference-standards'], queryFn: referenceStandardApi.list });
}
export function useCreateReferenceStandard() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: referenceStandardApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['reference-standards'] }) });
}

export function useChemicals() {
  return useQuery({ queryKey: ['chemicals'], queryFn: chemicalApi.list });
}
export function useCreateChemical() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: chemicalApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['chemicals'] }) });
}

export function useVolumetricSolutions() {
  return useQuery({ queryKey: ['volumetric-solutions'], queryFn: volumetricApi.list });
}
export function useCreateVolumetricSolution() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: volumetricApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['volumetric-solutions'] }) });
}

// Stability now has its own dedicated feature — see @features/stability/hooks/useStability.ts
