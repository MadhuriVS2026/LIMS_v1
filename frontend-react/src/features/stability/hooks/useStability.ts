/**
 * TanStack Query hooks for the Stability Management feature.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { stabilityApi } from '../api/stabilityApi';
import type {
  CancelProtocolRequest,
  CreateProtocolRequest,
  CreateReservePullRequest,
  EsignActionRequest,
  GenerateScheduleRequest,
  MatrixCellInput,
  SetReportSignatureNamesRequest,
  UpdateProtocolHeaderRequest,
} from '../models/stability.types';

export function useProtocolList() {
  return useQuery({ queryKey: ['stability-protocols'], queryFn: stabilityApi.listProtocols });
}

export function useProtocolDetail(id: number | undefined) {
  return useQuery({
    queryKey: ['stability-protocol', id],
    queryFn: () => stabilityApi.getProtocol(id as number),
    enabled: id != null,
  });
}

export function useCreateProtocol() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateProtocolRequest) => stabilityApi.createProtocol(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['stability-protocols'] }),
  });
}

export function useUpdateProtocolHeader() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: UpdateProtocolHeaderRequest }) =>
      stabilityApi.updateProtocolHeader(id, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['stability-protocol', variables.id] });
      qc.invalidateQueries({ queryKey: ['stability-protocols'] });
    },
  });
}

export function useCompleteProtocol() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => stabilityApi.completeProtocol(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['stability-protocol', id] });
      qc.invalidateQueries({ queryKey: ['stability-protocols'] });
    },
  });
}

export function useCancelProtocol() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: CancelProtocolRequest }) =>
      stabilityApi.cancelProtocol(id, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['stability-protocol', variables.id] });
      qc.invalidateQueries({ queryKey: ['stability-protocols'] });
    },
  });
}

export function useMatrix(protocolId: number | undefined) {
  return useQuery({
    queryKey: ['stability-matrix', protocolId],
    queryFn: () => stabilityApi.getMatrix(protocolId as number),
    enabled: protocolId != null,
  });
}

export function useSetMatrix() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ protocolId, cells }: { protocolId: number; cells: MatrixCellInput[] }) =>
      stabilityApi.setMatrix(protocolId, cells),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['stability-matrix', variables.protocolId] });
    },
  });
}

export function useCheckFormulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ protocolId, payload }: { protocolId: number; payload: EsignActionRequest }) =>
      stabilityApi.checkFormulation(protocolId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['stability-protocol', variables.protocolId] });
      qc.invalidateQueries({ queryKey: ['stability-protocols'] });
    },
  });
}

export function useCheckAnalytical() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ protocolId, payload }: { protocolId: number; payload: EsignActionRequest }) =>
      stabilityApi.checkAnalytical(protocolId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['stability-protocol', variables.protocolId] });
      qc.invalidateQueries({ queryKey: ['stability-protocols'] });
    },
  });
}

export function useGenerateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ protocolId, payload }: { protocolId: number; payload: GenerateScheduleRequest }) =>
      stabilityApi.generateSchedule(protocolId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['stability-samples', variables.protocolId] });
    },
  });
}

export function useSampleList(protocolId: number | undefined) {
  return useQuery({
    queryKey: ['stability-samples', protocolId],
    queryFn: () => stabilityApi.listSamples(protocolId as number),
    enabled: protocolId != null,
  });
}

export function usePullSample() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ stabilitySampleId }: { stabilitySampleId: number; protocolId: number }) =>
      stabilityApi.pullSample(stabilitySampleId),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['stability-samples', variables.protocolId] });
    },
  });
}

export function useCreateReservePull() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ protocolId, payload }: { protocolId: number; payload: CreateReservePullRequest }) =>
      stabilityApi.createReservePull(protocolId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['stability-samples', variables.protocolId] });
    },
  });
}

export function useGenerateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (protocolId: number) => stabilityApi.generateReport(protocolId),
    onSuccess: (_data, protocolId) => {
      qc.invalidateQueries({ queryKey: ['stability-reports', protocolId] });
    },
  });
}

export function useReportList(protocolId: number | undefined) {
  return useQuery({
    queryKey: ['stability-reports', protocolId],
    queryFn: () => stabilityApi.listReports(protocolId as number),
    enabled: protocolId != null,
  });
}

export function useReportDetail(id: number | undefined) {
  return useQuery({
    queryKey: ['stability-report', id],
    queryFn: () => stabilityApi.getReport(id as number),
    enabled: id != null,
  });
}

export function useSetReportSignatureNames() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      reportId,
      payload,
    }: {
      reportId: number;
      payload: SetReportSignatureNamesRequest;
      protocolId: number;
    }) => stabilityApi.setReportSignatureNames(reportId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['stability-report', variables.reportId] });
      qc.invalidateQueries({ queryKey: ['stability-reports', variables.protocolId] });
    },
  });
}

export function usePrepareReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ reportId, payload }: { reportId: number; payload: EsignActionRequest; protocolId: number }) =>
      stabilityApi.prepareReport(reportId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['stability-report', variables.reportId] });
      qc.invalidateQueries({ queryKey: ['stability-reports', variables.protocolId] });
    },
  });
}

export function useApproveReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ reportId, payload }: { reportId: number; payload: EsignActionRequest; protocolId: number }) =>
      stabilityApi.approveReport(reportId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['stability-report', variables.reportId] });
      qc.invalidateQueries({ queryKey: ['stability-reports', variables.protocolId] });
    },
  });
}
