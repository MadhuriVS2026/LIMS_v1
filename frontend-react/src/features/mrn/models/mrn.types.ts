/**
 * MRN — Material Requisition & Consumption domain types.
 */
export interface MRNMaterialLot {
  id: number;
  grn_document_no: string;
  grn_item_no: string;
  material_code: string;
  material_description?: string | null;
  batch_number?: string | null;
  plant: string;
  unit: string;
  original_quantity: number;
  consumed_quantity: number;
  available_quantity: number;
  status: string;
  grn_date?: string | null;
  pulled_at?: string | null;
}

export interface MaterialQueuePullResponse {
  pulled: number;
  lots: MRNMaterialLot[];
}

export interface CreateLineItemRequest {
  lot_id: number;
  requested_quantity: number;
  project_code: string;
}

export interface MRNLineItem {
  id: number;
  mrn_id: number;
  line_no: number;
  lot_id: number;
  requested_quantity: number;
  project_code: string;
  status: string;
  lot_material_code?: string | null;
  lot_batch_number?: string | null;
  consumption_posting_id?: number | null;
}

export interface MaterialRequisition {
  id: number;
  mrn_number: string;
  status: string;
  created_by: string;
  created_date: string;
  submitted_by?: string | null;
  submitted_at?: string | null;
  posted_by?: string | null;
  posted_at?: string | null;
  line_items: MRNLineItem[];
}

export interface ApproveAndPostRequest {
  password: string;
  comments?: string;
}

export interface ConsumptionPosting {
  id: number;
  line_item_id: number;
  idempotency_key: string;
  status: string;
  sap_doc_no?: string | null;
  error_message?: string | null;
  posted_at?: string | null;
}
