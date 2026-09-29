/**
 * TRF attachment API calls.
 */
import { apiClient } from '@shared/services/apiClient';
import type {
  AttachmentLimits,
  TRFAttachment,
  UploadAttachmentRequest,
} from '../models/attachment.types';

export const attachmentApi = {
  async limits(): Promise<AttachmentLimits> {
    return (await apiClient.get<AttachmentLimits>('/attachments/limits')).data;
  },

  async listForTrf(trfId: number): Promise<TRFAttachment[]> {
    return (await apiClient.get<TRFAttachment[]>(`/trf/${trfId}/attachments`)).data;
  },

  async listForTestLine(lineId: number): Promise<TRFAttachment[]> {
    return (await apiClient.get<TRFAttachment[]>(`/trf/test-lines/${lineId}/attachments`)).data;
  },

  async upload(trfId: number, payload: UploadAttachmentRequest): Promise<TRFAttachment> {
    const form = new FormData();
    form.append('file', payload.file);
    if (payload.testLineId != null) form.append('test_line_id', String(payload.testLineId));
    if (payload.description) form.append('description', payload.description);

    //  Content-Type is left unset on purpose: the browser must supply it so the
    //  multipart boundary is included. Setting it by hand breaks the upload.
    return (await apiClient.post<TRFAttachment>(`/trf/${trfId}/attachments`, form)).data;
  },

  async remove(attachmentId: number, reason?: string | null): Promise<void> {
    await apiClient.delete(`/attachments/${attachmentId}`, {
      params: reason ? { reason } : undefined,
    });
  },

  /**
   * Fetches the bytes and saves them via a temporary object URL.
   *
   * A plain `<a href>` cannot be used: the download endpoint requires the bearer
   * token, which a browser-initiated navigation would not send.
   */
  async download(attachment: TRFAttachment): Promise<void> {
    const response = await apiClient.get(`/attachments/${attachment.id}/download`, {
      responseType: 'blob',
    });

    const url = URL.createObjectURL(response.data as Blob);
    try {
      const link = document.createElement('a');
      link.href = url;
      link.download = attachment.original_filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
    } finally {
      //  Revoke on the next tick — revoking synchronously can cancel the download
      //  in some browsers before it has started.
      setTimeout(() => URL.revokeObjectURL(url), 0);
    }
  },
};
