/**
 * Test template API calls.
 */
import { apiClient } from '@shared/services/apiClient';
import type {
  CreateTemplateRequest,
  EsignActionRequest,
  TestTemplate,
  TestTemplateSummary,
  UpdateDefinitionRequest,
  UpdateTemplateHeaderRequest,
} from '../models/testTemplate.types';

export const testTemplateApi = {
  async list(params?: { testId?: number; status?: string }): Promise<TestTemplateSummary[]> {
    const query: Record<string, string | number> = {};
    if (params?.testId != null) query.test_id = params.testId;
    if (params?.status) query.status = params.status;
    return (await apiClient.get<TestTemplateSummary[]>('/test-templates', { params: query })).data;
  },
  async get(id: number): Promise<TestTemplate> {
    return (await apiClient.get<TestTemplate>(`/test-templates/${id}`)).data;
  },
  /** Only Active templates, i.e. what a TRF test line may attach. */
  async forTest(testId: number): Promise<TestTemplateSummary[]> {
    return (await apiClient.get<TestTemplateSummary[]>(`/test-templates/for-test/${testId}`)).data;
  },
  async versions(id: number): Promise<TestTemplateSummary[]> {
    return (await apiClient.get<TestTemplateSummary[]>(`/test-templates/${id}/versions`)).data;
  },
  async create(payload: CreateTemplateRequest): Promise<TestTemplate> {
    return (await apiClient.post<TestTemplate>('/test-templates', payload)).data;
  },
  async updateDefinition(id: number, payload: UpdateDefinitionRequest): Promise<TestTemplate> {
    return (await apiClient.put<TestTemplate>(`/test-templates/${id}/definition`, payload)).data;
  },
  async updateHeader(id: number, payload: UpdateTemplateHeaderRequest): Promise<TestTemplate> {
    return (await apiClient.put<TestTemplate>(`/test-templates/${id}`, payload)).data;
  },
  async submit(id: number): Promise<TestTemplate> {
    return (await apiClient.post<TestTemplate>(`/test-templates/${id}/submit`)).data;
  },
  async approve(id: number, payload: EsignActionRequest): Promise<TestTemplate> {
    return (await apiClient.post<TestTemplate>(`/test-templates/${id}/approve`, payload)).data;
  },
  async reject(id: number, reason: string): Promise<TestTemplate> {
    return (await apiClient.post<TestTemplate>(`/test-templates/${id}/reject`, { reason })).data;
  },
  async newVersion(id: number): Promise<TestTemplate> {
    return (await apiClient.post<TestTemplate>(`/test-templates/${id}/new-version`)).data;
  },
  async deactivate(id: number, reason?: string | null): Promise<TestTemplate> {
    return (await apiClient.post<TestTemplate>(`/test-templates/${id}/deactivate`, { reason })).data;
  },
};
