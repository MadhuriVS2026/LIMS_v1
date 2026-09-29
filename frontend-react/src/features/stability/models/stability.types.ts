/**
 * Stability Management domain types — mirrors backend
 * src/domain/entities/stability.py and stability_schemas.py exactly.
 */

// Standard day-based time points from the real Stability Protocol Format document.
export const STANDARD_TIME_POINT_DAYS = [15, 30, 60, 90, 180, 270, 365, 545, 730, 1095];

// Suggested (not enforced) condition values from the real document.
export const SUGGESTED_CONDITIONS = [
  '40°C±2°C/75%±5%RH',
  '30°C±2°C/65%±5%RH',
  '30°C±2°C/75%±5%RH',
  '25°C±2°C/60%±5%RH',
  '5°C±3°C',
  'Other',
];

export const STUDY_TYPES = ['Long Term', 'Accelerated', 'Intermediate'];

export interface CreateProtocolRequest {
  product_id: number;
  condition: string;
  duration_months: number;
  study_type?: string;
  testing_frequency?: string;
  label_claim?: string;
  mfg_date?: string;
  batch_number?: string;
  placebo_batch_number?: string;
  batch_size?: string;
  stability_initiation_date?: string;
  no_of_samples_time_points?: string;
  fill_volume?: string;
  api_name?: string;
  api_batch_no?: string;
  api_source?: string;
  primary_pack?: string;
  secondary_pack?: string;
  headspace?: string;
  orientation?: string;
  remarks?: string;
}

export interface StabilityProtocol {
  id: number;
  protocol_code: string;
  product_id: number;
  condition: string;
  duration_months: number;
  study_type?: string | null;
  testing_frequency?: string | null;
  status: string; // Draft, FormulationChecked, Active, Completed, Cancelled
  label_claim?: string | null;
  mfg_date?: string | null;
  batch_number?: string | null;
  placebo_batch_number?: string | null;
  batch_size?: string | null;
  stability_initiation_date?: string | null;
  no_of_samples_time_points?: string | null;
  fill_volume?: string | null;
  api_name?: string | null;
  api_batch_no?: string | null;
  api_source?: string | null;
  primary_pack?: string | null;
  secondary_pack?: string | null;
  headspace?: string | null;
  orientation?: string | null;
  remarks?: string | null;
  formulation_checked_by?: string | null;
  formulation_checked_at?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  created_by: string;
  created_date: string;
}

export interface MatrixCellInput {
  id?: number | null;
  condition: string;
  is_reserve: boolean;
  time_point_days?: number | null;
  is_scheduled: boolean;
  notes?: string | null;
}

export interface StabilityMatrixCell {
  id: number;
  protocol_id: number;
  condition: string;
  is_reserve: boolean;
  time_point_days?: number | null;
  time_point_month_label?: string | null;
  is_scheduled: boolean;
  notes?: string | null;
}

export interface EsignActionRequest {
  password: string;
  comments?: string;
}

export interface GenerateScheduleRequest {
  batch_numbers: string[];
}

export interface UpdateProtocolHeaderRequest {
  condition?: string;
  duration_months?: number;
  study_type?: string;
  testing_frequency?: string;
  label_claim?: string;
  mfg_date?: string;
  batch_number?: string;
  placebo_batch_number?: string;
  batch_size?: string;
  stability_initiation_date?: string;
  no_of_samples_time_points?: string;
  fill_volume?: string;
  api_name?: string;
  api_batch_no?: string;
  api_source?: string;
  primary_pack?: string;
  secondary_pack?: string;
  headspace?: string;
  orientation?: string;
  remarks?: string;
}

export interface CancelProtocolRequest {
  reason?: string;
}

export interface CreateReservePullRequest {
  matrix_cell_id: number;
  batch_number: string;
  comments?: string;
}

export interface SetReportSignatureNamesRequest {
  checked_by_name?: string;
  reviewed_by_name?: string;
}

export interface StabilitySample {
  id: number;
  protocol_id: number;
  matrix_cell_id: number;
  condition: string;
  time_point_days?: number | null;
  time_point_months: number;
  batch_number: string;
  scheduled_date?: string | null;
  pull_date?: string | null;
  sample_id?: number | null;
  comments?: string | null;
  status: string; // Scheduled, Pulled, Testing, Completed
}

export interface StabilityReport {
  id: number;
  protocol_id: number;
  report_number: string;
  status: string; // Draft, Prepared, Approved
  product_name?: string | null;
  composition_label?: string | null;
  manufactured_at?: string | null;
  stability_study_type?: string | null;
  batch_no?: string | null;
  stability_condition?: string | null;
  batch_size?: string | null;
  date_of_commencement?: string | null;
  manufacturing_date?: string | null;
  stability_protocol_no?: string | null;
  expiry_date?: string | null;
  api_source?: string | null;
  api_batch_number?: string | null;
  packing?: string | null;
  results_data: Array<{
    test_id: number;
    test_name: string;
    specification: string;
    results: Record<string, unknown>;
  }>;
  remarks?: string | null;
  prepared_by?: string | null;
  prepared_at?: string | null;
  checked_by_name?: string | null;
  reviewed_by_name?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  generated_by?: string | null;
  generated_at?: string | null;
}
