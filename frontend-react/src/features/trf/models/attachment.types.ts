/**
 * TRF attachment types.
 *
 * Note there is no `storage_name` — the backend deliberately does not expose it.
 * Downloads go through `/attachments/{id}/download` so they carry the same
 * authorisation as the rest of the TRF.
 */

export interface TRFAttachment {
  id: number;
  trf_id: number;
  trf_test_line_id: number | null;
  test_line_no: number | null;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  /** Formatted server-side so every client renders sizes identically. */
  size_display: string;
  /** SHA-256 of the stored bytes, for verifying a download. */
  checksum_sha256: string;
  description: string | null;
  uploaded_by: string;
  uploaded_at: string | null;
}

export interface AttachmentLimits {
  max_bytes: number;
  allowed_content_types: string[];
}

export interface UploadAttachmentRequest {
  file: File;
  testLineId?: number | null;
  description?: string | null;
}
