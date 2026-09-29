/**
 * TanStack Query hooks for the TRF — Test Request Form feature.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { trfApi } from '../api/trfApi';
import type {
  CreateTestLineRequest,
  CreateTRFRequest,
  EsignActionRequest,
  ReferBackRejectRequest,
  SubmitTestResultRequest,
} from '../models/trf.types';

export function useTRFList() {
  return useQuery({ queryKey: ['trf-list'], queryFn: trfApi.list });
}

export function useTRFDetail(id: number | undefined) {
  return useQuery({
    queryKey: ['trf-detail', id],
    queryFn: () => trfApi.get(id as number),
    enabled: id != null,
  });
}

export function useATR(id: number | undefined) {
  return useQuery({
    queryKey: ['trf-atr', id],
    queryFn: () => trfApi.getATR(id as number),
    enabled: id != null,
  });
}

export function useCreateTRF() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateTRFRequest) => trfApi.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['trf-list'] }),
  });
}

export function useAddTestLine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trfId, payload }: { trfId: number; payload: CreateTestLineRequest }) =>
      trfApi.addTestLine(trfId, payload),
    onSuccess: (_data, variables) => qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] }),
  });
}

export function useRemoveTestLine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trfId, lineId }: { trfId: number; lineId: number }) => trfApi.removeTestLine(trfId, lineId),
    onSuccess: (_data, variables) => qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] }),
  });
}

export function useSubmitTRF() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (trfId: number) => trfApi.submit(trfId),
    onSuccess: (_data, trfId) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
    },
  });
}

export function useFdglApprove() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trfId, payload }: { trfId: number; payload: EsignActionRequest }) =>
      trfApi.fdglApprove(trfId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
    },
  });
}

export function useFdglReferBack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trfId, payload }: { trfId: number; payload: ReferBackRejectRequest }) =>
      trfApi.fdglReferBack(trfId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
    },
  });
}

export function useFdglReject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trfId, payload }: { trfId: number; payload: ReferBackRejectRequest }) =>
      trfApi.fdglReject(trfId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
    },
  });
}

export function useAdglAccept() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trfId, payload }: { trfId: number; payload: EsignActionRequest }) =>
      trfApi.adglAccept(trfId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
    },
  });
}

export function useAdglReferBack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trfId, payload }: { trfId: number; payload: ReferBackRejectRequest }) =>
      trfApi.adglReferBack(trfId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
    },
  });
}

export function useAdglReject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trfId, payload }: { trfId: number; payload: ReferBackRejectRequest }) =>
      trfApi.adglReject(trfId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
    },
  });
}

export function useAnalystAccept() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (trfId: number) => trfApi.analystAccept(trfId),
    onSuccess: (_data, trfId) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
    },
  });
}

export function useAnalystReferBack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trfId, payload }: { trfId: number; payload: ReferBackRejectRequest }) =>
      trfApi.analystReferBack(trfId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
    },
  });
}

export function useAnalystReject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trfId, payload }: { trfId: number; payload: ReferBackRejectRequest }) =>
      trfApi.analystReject(trfId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
    },
  });
}

export function useSubmitTestResult() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      lineId,
      trfId,
      payload,
    }: {
      lineId: number;
      trfId: number;
      payload: SubmitTestResultRequest;
    }) => trfApi.submitTestResult(lineId, payload),
    onSuccess: (_data, variables) => qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] }),
  });
}

export function useSubmitResults() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trfId, payload }: { trfId: number; payload: EsignActionRequest }) =>
      trfApi.submitResults(trfId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
    },
  });
}

export function useReleaseResults() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trfId, payload }: { trfId: number; payload: EsignActionRequest }) =>
      trfApi.release(trfId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', variables.trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
      qc.invalidateQueries({ queryKey: ['trf-atr', variables.trfId] });
    },
  });
}

export function useResubmitTRF() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (trfId: number) => trfApi.resubmit(trfId),
    onSuccess: (_data, trfId) => {
      qc.invalidateQueries({ queryKey: ['trf-detail', trfId] });
      qc.invalidateQueries({ queryKey: ['trf-list'] });
    },
  });
}
