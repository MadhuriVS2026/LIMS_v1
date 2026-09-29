/**
 * Certificate of Analysis types.
 *
 * The snapshot is typed loosely on purpose. It is an immutable historical
 * document: a certificate issued today must still render years from now, so the
 * print page reads defensively rather than assuming a fixed shape.
 */

export type Verdict = 'Pass' | 'Fail' | 'NotEvaluated';
export type ResultSource = 'Worksheet' | 'FreeText';

export interface COATestRow {
  test_id: number;
  test_code: string | null;
  test_name: string | null;
  specification_text: string;
  result_text: string;
  verdict: Verdict;
  /** `Worksheet` when a template produced the number, `FreeText` when typed. */
  source: ResultSource;
  trf_number: string | null;
  ar_number: string | null;
  template_code: string | null;
  template_version: number | null;
  numeric_result: number | null;
  unit: string | null;
  min_limit: number | null;
  max_limit: number | null;
  limit_unit: string | null;
  /**
   * Why a row could not be judged. Set whenever `verdict` is `NotEvaluated` —
   * a missing result, absent limits, or units that do not agree.
   */
  not_evaluated_reason: string | null;
}

export interface COASignatureChain {
  trf_number: string;
  ar_number: string | null;
  initiated_by: string | null;
  initiated_at: string | null;
  fdgl_approved_by: string | null;
  fdgl_approved_at: string | null;
  adgl_accepted_by: string | null;
  adgl_accepted_at: string | null;
  analyst_accepted_by: string | null;
  analyst_accepted_at: string | null;
  results_submitted_by: string | null;
  results_submitted_at: string | null;
  released_by: string | null;
  released_at: string | null;
}

export interface COASnapshot {
  /** `null` on a preview — that is how a preview is told from an issued COA. */
  coa_number: string | null;
  generated_at: string;
  product: {
    id: number;
    code: string;
    name: string;
    material_type: string | null;
    storage_condition: string | null;
  };
  batch: {
    batch_number: string;
    label_claim: string | null;
    stage_of_sample: string | null;
    pack_details: string | null;
    manufactured_by: string | null;
    mfg_date: string | null;
    expiry_or_retest_date: string | null;
    quantity: string | null;
    storage_condition: string | null;
  };
  references: {
    trf_numbers: string[];
    ar_numbers: string[];
  };
  specification: {
    id: number;
    version: number;
    document_no: string | null;
    spec_type: string | null;
    approved_by: string | null;
  } | null;
  tests: COATestRow[];
  overall_verdict: Verdict;
  verdict_counts: Record<Verdict, number>;
  signatures: COASignatureChain[];
  issued_by: { username: string; full_name: string; role: string } | null;
  remarks: string | null;
}

export interface COASummary {
  id: number;
  coa_number: string;
  product_id: number;
  product_code: string | null;
  product_name: string | null;
  batch_number: string;
  status: string;
  overall_verdict: Verdict;
  test_count: number;
  released_by: string;
  released_at: string | null;
}

export interface COA extends COASummary {
  snapshot: COASnapshot;
}

export interface GenerateCOARequest {
  product_id: number;
  batch_number: string;
  remarks?: string | null;
  password: string;
}

export interface PreviewCOARequest {
  product_id: number;
  batch_number: string;
}
