/**
 * TanStack Query hooks for the Sample Manager feature.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { productApi, sampleApi, specificationApi, testApi, resultApi } from '../api/sampleApi';
import { oosApi } from '../api/oosApi';
import type { CreateSampleRequest, Product, SpecTestItem, SubmitResultRequest } from '../models/sample.types';

export function useProducts() {
  return useQuery({ queryKey: ['products'], queryFn: productApi.list });
}

export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: productApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  });
}

export function useApproveProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, password, comments }: { id: number; password: string; comments?: string }) =>
      productApi.approve(id, password, comments),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  });
}

export function useUpdateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<Product> }) =>
      productApi.update(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  });
}

export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, password, comments }: { id: number; password: string; comments?: string }) =>
      productApi.remove(id, password, comments),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  });
}

export function useTests() {
  return useQuery({ queryKey: ['tests'], queryFn: testApi.list });
}

export function useCreateTest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: testApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tests'] }),
  });
}

export function useSpecifications() {
  return useQuery({ queryKey: ['specifications'], queryFn: specificationApi.list });
}

export function useCreateSpecification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { product_id: number; spec_type?: string; document_no?: string; tests: SpecTestItem[] }) =>
      specificationApi.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['specifications'] }),
  });
}

export function useApproveSpecification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, password, comments }: { id: number; password: string; comments?: string }) =>
      specificationApi.approve(id, password, comments),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['specifications'] }),
  });
}

export function useUpdateSpecification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { spec_type?: string; document_no?: string; tests?: SpecTestItem[] } }) =>
      specificationApi.update(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['specifications'] }),
  });
}

export function useDeleteSpecification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, password, comments }: { id: number; password: string; comments?: string }) =>
      specificationApi.remove(id, password, comments),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['specifications'] }),
  });
}

export function useSampleList(status?: string) {
  return useQuery({ queryKey: ['samples', status], queryFn: () => sampleApi.list(status) });
}

export function useCreateSample() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateSampleRequest) => sampleApi.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['samples'] }),
  });
}

export function useReceiveSample() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => sampleApi.receive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['samples'] }),
  });
}

export function useUpdateSample() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<CreateSampleRequest> }) =>
      sampleApi.update(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['samples'] }),
  });
}

export function useDeleteSample() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, password, comments }: { id: number; password: string; comments?: string }) =>
      sampleApi.remove(id, password, comments),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['samples'] }),
  });
}

export function useReleaseSample() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, verdict, password, comments }: { id: number; verdict: string; password: string; comments?: string }) =>
      sampleApi.release(id, verdict, password, comments),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['samples'] }),
  });
}

export function useGetCoa() {
  return useMutation({
    mutationFn: (id: number) => sampleApi.getCoa(id),
  });
}

export function useSubmitResult() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ resultId, payload }: { resultId: number; payload: SubmitResultRequest }) =>
      resultApi.submit(resultId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['samples'] });
      qc.invalidateQueries({ queryKey: ['oos'] });
    },
  });
}

export function useReviewResult() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ resultId, password, comments }: { resultId: number; password: string; comments?: string }) =>
      resultApi.review(resultId, password, comments),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['samples'] }),
  });
}

export function useOOSList() {
  return useQuery({ queryKey: ['oos'], queryFn: oosApi.list });
}

export function useCloseOOS() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, rootCause, correctiveAction, password }: { id: number; rootCause: string; correctiveAction: string; password: string }) =>
      oosApi.close(id, rootCause, correctiveAction, password),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['oos'] });
      qc.invalidateQueries({ queryKey: ['samples'] });
    },
  });
}
