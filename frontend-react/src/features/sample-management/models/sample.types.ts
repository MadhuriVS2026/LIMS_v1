/**
 * Sample Manager domain types.
 */
export interface Product {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  material_type?: string | null;
  retest_period_days?: number | null;
  storage_condition?: string | null;
  status: string;
  created_by?: string | null;
  created_date?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
}

export interface TestParameter {
  id: number;
  code: string;
  name: string;
  type: string;
  unit?: string | null;
  method_no?: string | null;
  category?: string | null;
  technique?: string | null;
  status: string;
}

export interface SpecTestItem {
  test_id: number;
  min_limit?: number | null;
  max_limit?: number | null;
  expected_result?: string | null;
  display_in_coa?: boolean;
}

export interface SpecTestResponse extends SpecTestItem {
  id: number;
  test?: TestParameter;
}

export interface Specification {
  id: number;
  product_id: number;
  version: number;
  spec_type?: string | null;
  document_no?: string | null;
  status: string;
  created_by?: string | null;
  created_date?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  tests: SpecTestResponse[];
  product?: Product;
}

export interface SampleResult {
  id: number;
  sample_id: number;
  test_id: number;
  min_limit?: number | null;
  max_limit?: number | null;
  expected_result?: string | null;
  result_value?: number | null;
  result_text?: string | null;
  status: string;
  is_oos: boolean;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  test?: TestParameter;
}

export interface Sample {
  id: number;
  sample_code: string;
  product_id: number;
  batch_number: string;
  quantity_received: number;
  unit: string;
  sample_type?: string | null;
  priority?: string | null;
  status: string;
  sap_inspection_lot?: string | null;
  sap_ud_posted?: boolean;
  manufacturing_date?: string | null;
  expiry_date?: string | null;
  logged_by?: string | null;
  logged_at?: string | null;
  received_by?: string | null;
  received_at?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  coa_released_by?: string | null;
  coa_released_at?: string | null;
  coa_data?: Record<string, unknown> | null;
  product?: Product;
  results: SampleResult[];
}

export interface CreateSampleRequest {
  product_id: number;
  batch_number: string;
  quantity_received: number;
  unit: string;
  sample_type?: string;
  priority?: string;
  sap_inspection_lot?: string;
  sap_material?: string;
  sap_plant?: string;
  sap_vendor?: string;
  sap_vendor_batch?: string;
  manufacturing_date?: string;
  expiry_date?: string;
}

export interface SubmitResultRequest {
  result_value?: number | null;
  result_text?: string | null;
  password: string;
  comments?: string;
}
