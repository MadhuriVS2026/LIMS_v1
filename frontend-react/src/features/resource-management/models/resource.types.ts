/**
 * Resource Manager domain types: Instruments, Columns, Reference Standards,
 * Chemicals/Reagents, Volumetric Solutions, Stability Protocols/Samples.
 */
export interface Instrument {
  id: number;
  code: string;
  name: string;
  category?: string | null;
  manufacturer?: string | null;
  model_number?: string | null;
  serial_number?: string | null;
  location?: string | null;
  status: string;
  calibration_due_date?: string | null;
  calibration_frequency_days?: number | null;
  last_calibrated_at?: string | null;
  last_calibrated_by?: string | null;
  qualification_status?: string | null;
}

export interface ColumnMaster {
  id: number;
  code: string;
  name: string;
  type?: string | null;
  manufacturer?: string | null;
  dimensions?: string | null;
  serial_number?: string | null;
  instrument_id?: number | null;
  max_injections?: number | null;
  current_injections: number;
  status: string;
}

export interface ReferenceStandard {
  id: number;
  code: string;
  name: string;
  lot_number?: string | null;
  potency?: number | null;
  manufacturer?: string | null;
  category?: string | null;
  quantity_received?: number | null;
  quantity_remaining?: number | null;
  unit?: string | null;
  expiry_date?: string | null;
  status: string;
}

export interface ChemicalReagent {
  id: number;
  code: string;
  name: string;
  grade?: string | null;
  manufacturer?: string | null;
  lot_number?: string | null;
  cas_number?: string | null;
  quantity_received?: number | null;
  quantity_remaining?: number | null;
  unit?: string | null;
  expiry_date?: string | null;
  status: string;
}

export interface VolumetricSolution {
  id: number;
  code: string;
  name: string;
  concentration?: string | null;
  prepared_by?: string | null;
  prepared_date?: string | null;
  expiry_date?: string | null;
  standardization_factor?: number | null;
  status: string;
}

// Stability now has its own dedicated feature — see @features/stability/models/stability.types.ts
