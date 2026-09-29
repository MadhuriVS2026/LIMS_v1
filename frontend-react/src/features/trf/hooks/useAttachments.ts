/**
 * TanStack Query hooks for TRF attachments.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { attachmentApi } from '../api/attachmentApi';
import type { UploadAttachmentRequest } from '../models/attachment.types';

export function useAttachmentLimits() {
  return useQuery({
    queryKey: ['attachment-limits'],
    queryFn: attachmentApi.limits,
    //  Configuration, not data — it changes only on deployment.
    staleTime: Infinity,
  });
}

export function useTrfAttachments(trfId: number | undefined) {
  return useQuery({
    queryKey: ['trf-attachments', trfId],
    queryFn: () => attachmentApi.listForTrf(trfId as number),
    enabled: trfId != null,
  });
}

export function useTestLineAttachments(lineId: number | undefined) {
  return useQuery({
    queryKey: ['test-line-attachments', lineId],
    queryFn: () => attachmentApi.listForTestLine(lineId as number),
    enabled: lineId != null,
  });
}

/**
 * Invalidates both scopes.
 *
 * A line-scoped file appears in the TRF list as well as its line's list, so
 * invalidating only the one it was uploaded against would leave the other stale.
 */
function useAttachmentInvalidation() {
  const qc = useQueryClient();
  return (trfId?: number) => {
    if (trfId != null) qc.invalidateQueries({ queryKey: ['trf-attachments', trfId] });
    qc.invalidateQueries({ queryKey: ['test-line-attachments'] });
  };
}

export function useUploadAttachment() {
  const invalidate = useAttachmentInvalidation();
  return useMutation({
    mutationFn: ({ trfId, payload }: { trfId: number; payload: UploadAttachmentRequest }) =>
      attachmentApi.upload(trfId, payload),
    onSuccess: (_data, variables) => invalidate(variables.trfId),
  });
}

export function useDeleteAttachment() {
  const invalidate = useAttachmentInvalidation();
  return useMutation({
    mutationFn: ({
      attachmentId,
      reason,
    }: {
      attachmentId: number;
      reason?: string | null;
      trfId?: number;
    }) => attachmentApi.remove(attachmentId, reason),
    onSuccess: (_data, variables) => invalidate(variables.trfId),
  });
}
