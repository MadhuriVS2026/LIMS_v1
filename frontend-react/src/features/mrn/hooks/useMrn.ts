/**
 * TanStack Query hooks for the MRN — Material Requisition & Consumption feature.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { mrnApi } from '../api/mrnApi';
import type { ApproveAndPostRequest, CreateLineItemRequest } from '../models/mrn.types';

export function useMaterialQueue() {
  return useQuery({ queryKey: ['mrn-material-queue'], queryFn: mrnApi.getMaterialQueue });
}

export function usePullMaterialQueue() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mrnApi.pullMaterialQueue,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mrn-material-queue'] }),
  });
}

export function useMRNList() {
  return useQuery({ queryKey: ['mrn-list'], queryFn: mrnApi.list });
}

export function useMRNDetail(id: number | undefined) {
  return useQuery({
    queryKey: ['mrn-detail', id],
    queryFn: () => mrnApi.get(id as number),
    enabled: id != null,
  });
}

export function useCreateMRN() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mrnApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mrn-list'] }),
  });
}

export function useAddLineItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ mrnId, payload }: { mrnId: number; payload: CreateLineItemRequest }) =>
      mrnApi.addLineItem(mrnId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['mrn-detail', variables.mrnId] });
      qc.invalidateQueries({ queryKey: ['mrn-material-queue'] });
    },
  });
}

export function useRemoveLineItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ mrnId, lineId }: { mrnId: number; lineId: number }) => mrnApi.removeLineItem(mrnId, lineId),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['mrn-detail', variables.mrnId] });
      qc.invalidateQueries({ queryKey: ['mrn-material-queue'] });
    },
  });
}

export function useSubmitMRN() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mrnId: number) => mrnApi.submit(mrnId),
    onSuccess: (_data, mrnId) => {
      qc.invalidateQueries({ queryKey: ['mrn-detail', mrnId] });
      qc.invalidateQueries({ queryKey: ['mrn-list'] });
    },
  });
}

export function useApproveAndPostMRN() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ mrnId, payload }: { mrnId: number; payload: ApproveAndPostRequest }) =>
      mrnApi.approveAndPost(mrnId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['mrn-detail', variables.mrnId] });
      qc.invalidateQueries({ queryKey: ['mrn-list'] });
      qc.invalidateQueries({ queryKey: ['mrn-material-queue'] });
    },
  });
}

export function useReprocessMRN() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mrnId: number) => mrnApi.reprocess(mrnId),
    onSuccess: (_data, mrnId) => {
      qc.invalidateQueries({ queryKey: ['mrn-detail', mrnId] });
      qc.invalidateQueries({ queryKey: ['mrn-list'] });
      qc.invalidateQueries({ queryKey: ['mrn-material-queue'] });
    },
  });
}
