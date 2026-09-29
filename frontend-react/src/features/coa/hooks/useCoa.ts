/**
 * TanStack Query hooks for Certificates of Analysis.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { coaApi } from '../api/coaApi';
import type { GenerateCOARequest, PreviewCOARequest } from '../models/coa.types';

export function useCoaList(params?: { productId?: number; batchNumber?: string }) {
  return useQuery({
    queryKey: ['coa-list', params?.productId ?? null, params?.batchNumber ?? null],
    queryFn: () => coaApi.list(params),
  });
}

export function useCoa(id: number | undefined) {
  return useQuery({
    queryKey: ['coa', id],
    queryFn: () => coaApi.get(id as number),
    enabled: id != null,
    //  A certificate is immutable, so once fetched it never needs refetching.
    staleTime: Infinity,
  });
}

export function useGenerateCoa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: GenerateCOARequest) => coaApi.generate(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['coa-list'] }),
  });
}

/**
 * Compilation preview, as a mutation rather than a query.
 *
 * It is a POST over a product/batch pair rather than a resource with its own URL,
 * and QA triggers it explicitly before signing — caching it by key would mean
 * showing a stale compilation after new results were released.
 */
export function usePreviewCoa() {
  return useMutation({
    mutationFn: (payload: PreviewCOARequest) => coaApi.preview(payload),
  });
}
