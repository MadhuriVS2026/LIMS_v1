/**
 * TRF — Test Request Form domain types.
 */
export interface CreateTRFRequest {
  product_id: number;
  batch_number: string;
  label_claim?: string;
  stage_of_sample?: string;
  group_name?: string;
  quantity?: string;
  storage_condition?: string;
  storage_period?: string;
  pack_details?: string;
  manufactured_by?: string;
  mfg_date?: string;
  expiry_or_retest_date?: string;
  remark?: string;
}

export interface CreateTestLineRequest {
  test_id: number;
  specification?: string;
  raw_data_reference?: string;
  remark?: string;
}

export interface TRFTestLine {
  id: number;
  trf_id: number;
  line_no: number;
  test_id: number;
  test_code?: string | null;
  test_name?: string | null;
  specification?: string | null;
  raw_data_reference?: string | null;
  result?: string | null;
  remark?: string | null;
  status: string;
}

export interface TestRequestForm {
  id: number;
  trf_number: string;
  ar_number?: string | null;
  product_id: number;
  batch_number: string;
  label_claim?: string | null;
  stage_of_sample?: string | null;
  group_name?: string | null;
  quantity?: string | null;
  storage_condition?: string | null;
  storage_period?: string | null;
  pack_details?: string | null;
  manufactured_by?: string | null;
  mfg_date?: string | null;
  expiry_or_retest_date?: string | null;
  remark?: string | null;
  source: string;
  status: string;
  created_by: string;
  created_date: string;
  initiated_by?: string | null;
  initiated_at?: string | null;
  fdgl_approved_by?: string | null;
  fdgl_approved_at?: string | null;
  adgl_accepted_by?: string | null;
  adgl_accepted_at?: string | null;
  analyst_accepted_by?: string | null;
  analyst_accepted_at?: string | null;
  results_submitted_by?: string | null;
  results_submitted_at?: string | null;
  released_by?: string | null;
  released_at?: string | null;
  referred_back_by?: string | null;
  referred_back_at?: string | null;
  referred_back_comments?: string | null;
  rejected_by?: string | null;
  rejected_at?: string | null;
  rejected_comments?: string | null;
  test_lines: TRFTestLine[];
}

export interface SubmitTestResultRequest {
  result?: string | null;
  remark?: string | null;
}

export interface EsignActionRequest {
  password: string;
}

export interface ReferBackRejectRequest {
  comments: string;
}

export interface ATRResponse {
  trf_number: string;
  ar_number?: string | null;
  product_id: number;
  batch_number: string;
  label_claim?: string | null;
  stage_of_sample?: string | null;
  storage_condition?: string | null;
  storage_period?: string | null;
  pack_details?: string | null;
  manufactured_by?: string | null;
  mfg_date?: string | null;
  expiry_or_retest_date?: string | null;
  remark?: string | null;
  test_lines: {
    line_no: number;
    test_id: number;
    test_code?: string | null;
    test_name?: string | null;
    specification?: string | null;
    raw_data_reference?: string | null;
    result?: string | null;
    remark?: string | null;
  }[];
  signatures: {
    initiated_by?: string | null;
    initiated_at?: string | null;
    approved_by?: string | null;
    approved_at?: string | null;
    accepted_by?: string | null;
    accepted_at?: string | null;
    analysed_by?: string | null;
    analysed_at?: string | null;
    released_by?: string | null;
    released_at?: string | null;
  };
}
