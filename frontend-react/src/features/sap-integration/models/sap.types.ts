export interface SAPUsageDecisionResponse {
  success: boolean;
  message: string;
  inspection_lot?: string;
}

export interface SAPInspectionCharacteristic {
  InspectionLot?: string | null;
  characteristicNum?: string | null;
  testName?: string | null;
  uom?: string | null;
  targetValue?: string | null;
  upperTolLimit?: string | null;
  lowerTolLimit?: string | null;
}

export interface SAPReceivedLot {
  id: number;
  inspection_lot: string;
  plant?: string | null;
  material_number?: string | null;
  material_desc?: string | null;
  batch_number?: string | null;
  storage_location?: string | null;
  vendor_code?: string | null;
  vendor_name?: string | null;
  vendor_batch?: string | null;
  lot_quantity?: string | null;
  lot_unit?: string | null;
  manufacturing_date?: string | null;
  expiry_date?: string | null;
  characteristics: SAPInspectionCharacteristic[];
  received_at?: string | null;
  consumed_by_sample_id?: number | null;
}

export interface SAPIntegrationLog {
  id: number;
  transaction_type: string;
  direction: string;
  sample_id?: number | null;
  sap_inspection_lot?: string | null;
  status: string;
  created_by?: string | null;
  created_at?: string | null;
}
