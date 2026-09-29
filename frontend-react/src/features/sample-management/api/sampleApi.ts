/**
 * Sample Manager API calls: Products, Tests, Specifications, Samples, Results, OOS.
 */
import { apiClient } from '@shared/services/apiClient';
import type {
  CreateSampleRequest,
  Product,
  Sample,
  SampleResult,
  Specification,
  SpecTestItem,
  SubmitResultRequest,
  TestParameter,
} from '../models/sample.types';

export const productApi = {
  async list(): Promise<Product[]> {
    return (await apiClient.get<Product[]>('/products')).data;
  },
  async create(payload: Partial<Product>): Promise<Product> {
    return (await apiClient.post<Product>('/products', payload)).data;
  },
  async approve(id: number, password: string, comments?: string): Promise<Product> {
    return (await apiClient.post<Product>(`/products/${id}/approve`, { password, comments })).data;
  },
};

export const testApi = {
  async list(): Promise<TestParameter[]> {
    return (await apiClient.get<TestParameter[]>('/tests')).data;
  },
  async create(payload: Partial<TestParameter>): Promise<TestParameter> {
    return (await apiClient.post<TestParameter>('/tests', payload)).data;
  },
};

export const specificationApi = {
  async list(): Promise<Specification[]> {
    return (await apiClient.get<Specification[]>('/specifications')).data;
  },
  async create(payload: {
    product_id: number;
    spec_type?: string;
    document_no?: string;
    tests: SpecTestItem[];
  }): Promise<Specification> {
    return (await apiClient.post<Specification>('/specifications', payload)).data;
  },
  async approve(id: number, password: string, comments?: string): Promise<Specification> {
    return (await apiClient.post<Specification>(`/specifications/${id}/approve`, { password, comments })).data;
  },
};

export const sampleApi = {
  async list(status?: string): Promise<Sample[]> {
    return (await apiClient.get<Sample[]>('/samples', { params: status ? { status } : {} })).data;
  },
  async create(payload: CreateSampleRequest): Promise<Sample> {
    return (await apiClient.post<Sample>('/samples', payload)).data;
  },
  async receive(id: number): Promise<Sample> {
    return (await apiClient.post<Sample>(`/samples/${id}/receive`)).data;
  },
  async release(id: number, verdict: string, password: string, comments?: string): Promise<Sample> {
    return (
      await apiClient.post<Sample>(`/samples/${id}/release`, { password, comments }, { params: { verdict } })
    ).data;
  },
  async getCoa(id: number): Promise<Record<string, unknown>> {
    return (await apiClient.get(`/samples/${id}/coa`)).data;
  },
};

export const resultApi = {
  async submit(resultId: number, payload: SubmitResultRequest): Promise<SampleResult> {
    return (await apiClient.post<SampleResult>(`/results/${resultId}/submit`, payload)).data;
  },
  async review(resultId: number, password: string, comments?: string): Promise<SampleResult> {
    return (await apiClient.post<SampleResult>(`/results/${resultId}/review`, { password, comments })).data;
  },
};
