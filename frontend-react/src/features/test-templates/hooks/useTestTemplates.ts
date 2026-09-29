/**
 * TanStack Query hooks for test templates.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { testTemplateApi } from '../api/testTemplateApi';
import type {
  CreateTemplateRequest,
  EsignActionRequest,
  UpdateDefinitionRequest,
  UpdateTemplateHeaderRequest,
} from '../models/testTemplate.types';

export function useTemplateList(params?: { testId?: number; status?: string }) {
  return useQuery({
    queryKey: ['template-list', params?.testId ?? null, params?.status ?? null],
    queryFn: () => testTemplateApi.list(params),
  });
}

export function useTemplateDetail(id: number | undefined) {
  return useQuery({
    queryKey: ['template-detail', id],
    queryFn: () => testTemplateApi.get(id as number),
    enabled: id != null,
  });
}

/** Active templates for a Test — what a TRF test line may attach. */
export function useTemplatesForTest(testId: number | undefined) {
  return useQuery({
    queryKey: ['templates-for-test', testId],
    queryFn: () => testTemplateApi.forTest(testId as number),
    enabled: testId != null,
  });
}

export function useTemplateVersions(id: number | undefined) {
  return useQuery({
    queryKey: ['template-versions', id],
    queryFn: () => testTemplateApi.versions(id as number),
    enabled: id != null,
  });
}

/**
 * Invalidates everything a template mutation can affect.
 *
 * Approval supersedes an *other* template row and changes which templates are
 * selectable, so a targeted invalidation of the mutated id alone would leave
 * both the list and the per-test picker stale.
 */
function useTemplateInvalidation() {
  const qc = useQueryClient();
  return (id?: number) => {
    qc.invalidateQueries({ queryKey: ['template-list'] });
    qc.invalidateQueries({ queryKey: ['templates-for-test'] });
    if (id != null) {
      qc.invalidateQueries({ queryKey: ['template-detail', id] });
      qc.invalidateQueries({ queryKey: ['template-versions', id] });
    }
  };
}

export function useCreateTemplate() {
  const invalidate = useTemplateInvalidation();
  return useMutation({
    mutationFn: (payload: CreateTemplateRequest) => testTemplateApi.create(payload),
    onSuccess: (data) => invalidate(data.id),
  });
}

export function useUpdateTemplateDefinition() {
  const invalidate = useTemplateInvalidation();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: UpdateDefinitionRequest }) =>
      testTemplateApi.updateDefinition(id, payload),
    onSuccess: (_data, variables) => invalidate(variables.id),
  });
}

export function useUpdateTemplateHeader() {
  const invalidate = useTemplateInvalidation();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: UpdateTemplateHeaderRequest }) =>
      testTemplateApi.updateHeader(id, payload),
    onSuccess: (_data, variables) => invalidate(variables.id),
  });
}

export function useSubmitTemplate() {
  const invalidate = useTemplateInvalidation();
  return useMutation({
    mutationFn: (id: number) => testTemplateApi.submit(id),
    onSuccess: (_data, id) => invalidate(id),
  });
}

export function useApproveTemplate() {
  const invalidate = useTemplateInvalidation();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: EsignActionRequest }) =>
      testTemplateApi.approve(id, payload),
    onSuccess: (_data, variables) => invalidate(variables.id),
  });
}

export function useRejectTemplate() {
  const invalidate = useTemplateInvalidation();
  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      testTemplateApi.reject(id, reason),
    onSuccess: (_data, variables) => invalidate(variables.id),
  });
}

export function useNewTemplateVersion() {
  const invalidate = useTemplateInvalidation();
  return useMutation({
    mutationFn: (id: number) => testTemplateApi.newVersion(id),
    onSuccess: (data, id) => {
      invalidate(id);
      invalidate(data.id);
    },
  });
}

export function useDeactivateTemplate() {
  const invalidate = useTemplateInvalidation();
  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string | null }) =>
      testTemplateApi.deactivate(id, reason),
    onSuccess: (_data, variables) => invalidate(variables.id),
  });
}
