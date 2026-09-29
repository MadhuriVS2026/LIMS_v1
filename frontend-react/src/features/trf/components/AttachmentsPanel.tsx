/**
 * TRF attachments panel — chromatogram PDFs and raw-data files.
 *
 * Client-side checks against `/attachments/limits` are a courtesy: they save a
 * round trip on an obviously wrong file. The server enforces type, signature and
 * size regardless, so this is never the thing keeping a bad file out.
 *
 * Upload and delete are hidden once the TRF is Released. That is a
 * records-integrity rule rather than a permission — not even an Admin can change
 * a released record's supporting files — so the buttons go for everyone.
 */
import { useRef, useState } from 'react';
import { Button } from 'primereact/button';
import { Column } from 'primereact/column';
import { DataTable } from 'primereact/datatable';
import { Dialog } from 'primereact/dialog';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { Message } from 'primereact/message';
import { getErrorMessage, toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import {
  useAttachmentLimits,
  useDeleteAttachment,
  useTrfAttachments,
  useUploadAttachment,
} from '../hooks/useAttachments';
import { attachmentApi } from '../api/attachmentApi';
import type { TRFAttachment } from '../models/attachment.types';
import type { TRFTestLine } from '../models/trf.types';

interface AttachmentsPanelProps {
  trfId: number;
  trfStatus: string;
  testLines: TRFTestLine[];
}

export const AttachmentsPanel = ({ trfId, trfStatus, testLines }: AttachmentsPanelProps) => {
  const { hasRole, username } = usePermissions();
  const { data: attachments = [], isLoading } = useTrfAttachments(trfId);
  const { data: limits } = useAttachmentLimits();
  const upload = useUploadAttachment();
  const remove = useDeleteAttachment();

  const fileInput = useRef<HTMLInputElement>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [testLineId, setTestLineId] = useState<number | null>(null);
  const [description, setDescription] = useState('');
  const [deleting, setDeleting] = useState<TRFAttachment | null>(null);
  const [deleteReason, setDeleteReason] = useState('');
  const [downloadingId, setDownloadingId] = useState<number | null>(null);

  const isReleased = trfStatus === 'Released';
  const canUpload = hasRole('Admin', 'Analyst') && !isReleased;

  const lineOptions = [
    { label: 'Whole TRF (not test-specific)', value: null },
    ...testLines.map((l) => ({
      label: `Line ${l.line_no} — ${l.test_name ?? l.test_code ?? `Test #${l.test_id}`}`,
      value: l.id,
    })),
  ];

  const resetForm = () => {
    setPendingFile(null);
    setTestLineId(null);
    setDescription('');
    if (fileInput.current) fileInput.current.value = '';
  };

  const handlePick = (file: File | null) => {
    if (!file) {
      setPendingFile(null);
      return;
    }
    if (limits) {
      if (file.size > limits.max_bytes) {
        toastService.warn(
          `${file.name} is ${(file.size / (1024 * 1024)).toFixed(1)}MB, over the ` +
            `${(limits.max_bytes / (1024 * 1024)).toFixed(0)}MB limit.`,
          'File Too Large',
        );
        if (fileInput.current) fileInput.current.value = '';
        return;
      }
      //  An empty `file.type` means the browser could not determine it. Let it
      //  through rather than guessing — the server will decide.
      if (file.type && !limits.allowed_content_types.includes(file.type.split(';')[0])) {
        toastService.warn(
          `${file.type} is not an accepted file type. Allowed: ` +
            limits.allowed_content_types.join(', '),
          'Unsupported File Type',
        );
        if (fileInput.current) fileInput.current.value = '';
        return;
      }
    }
    setPendingFile(file);
  };

  const handleUpload = () => {
    if (!pendingFile) return;
    upload.mutate(
      { trfId, payload: { file: pendingFile, testLineId, description: description.trim() || null } },
      {
        onSuccess: (saved) => {
          toastService.success(`${saved.original_filename} attached.`, 'Uploaded');
          resetForm();
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Upload Failed'),
      },
    );
  };

  const handleDownload = async (attachment: TRFAttachment) => {
    setDownloadingId(attachment.id);
    try {
      await attachmentApi.download(attachment);
    } catch (e) {
      toastService.error(getErrorMessage(e), 'Download Failed');
    } finally {
      setDownloadingId(null);
    }
  };

  const handleDelete = () => {
    if (!deleting) return;
    remove.mutate(
      { attachmentId: deleting.id, reason: deleteReason.trim() || null, trfId },
      {
        onSuccess: () => {
          toastService.success(`${deleting.original_filename} removed.`, 'Deleted');
          setDeleting(null);
          setDeleteReason('');
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Remove'),
      },
    );
  };

  //  Mirrors the backend rule: the uploader or an Admin, and never on a released
  //  TRF. Shown/hidden here only as a courtesy — the server is what enforces it.
  const canDelete = (attachment: TRFAttachment) =>
    !isReleased && (hasRole('Admin') || attachment.uploaded_by === username);

  return (
    <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
      <div className="flex justify-content-between align-items-center p-3 pb-2">
        <div>
          <h3 className="text-base font-semibold text-900 m-0">Attachments</h3>
          <p className="text-xs text-500 m-0 mt-1">
            Chromatograms and raw data supporting these results.
          </p>
        </div>
        {limits && canUpload && (
          <span className="text-xs text-500">
            Max {(limits.max_bytes / (1024 * 1024)).toFixed(0)}MB ·{' '}
            {limits.allowed_content_types.map((t) => t.split('/')[1]).join(', ')}
          </span>
        )}
      </div>

      {isReleased && (
        <div className="px-3 pb-2">
          <Message
            severity="info"
            className="w-full"
            text="This TRF is released. Its attachments are part of the reportable record and can no longer be added to or removed."
          />
        </div>
      )}

      {canUpload && (
        <div className="px-3 pb-3 flex flex-column gap-2">
          <div className="flex gap-2 align-items-end flex-wrap">
            <div>
              <label className="block text-xs text-500 mb-1" htmlFor="attachment-file">
                File
              </label>
              <input
                id="attachment-file"
                ref={fileInput}
                type="file"
                accept={limits?.allowed_content_types.join(',')}
                onChange={(e) => handlePick(e.target.files?.[0] ?? null)}
                className="text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-500 mb-1">Scope</label>
              <Dropdown
                value={testLineId}
                options={lineOptions}
                onChange={(e) => setTestLineId(e.value)}
                className="w-20rem"
                aria-label="Attachment scope"
              />
            </div>
            <div className="flex-grow-1" style={{ minWidth: '14rem' }}>
              <label className="block text-xs text-500 mb-1">Description</label>
              <InputText
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full"
                placeholder="e.g. Assay injection 1"
              />
            </div>
            <Button
              label="Attach"
              icon="pi pi-upload"
              onClick={handleUpload}
              loading={upload.isPending}
              disabled={!pendingFile}
            />
          </div>
        </div>
      )}

      <DataTable
        value={attachments}
        loading={isLoading}
        size="small"
        emptyMessage="No attachments on this TRF yet."
      >
        <Column
          header="File"
          body={(row: TRFAttachment) => (
            <div className="flex align-items-center gap-2">
              <i className={fileIcon(row.content_type)} />
              <span className="font-medium">{row.original_filename}</span>
            </div>
          )}
        />
        <Column
          header="Scope"
          body={(row: TRFAttachment) =>
            row.test_line_no != null ? `Line ${row.test_line_no}` : 'Whole TRF'
          }
        />
        <Column header="Description" body={(row: TRFAttachment) => row.description || '-'} />
        <Column field="size_display" header="Size" />
        <Column field="uploaded_by" header="Uploaded By" />
        <Column
          header="Uploaded"
          body={(row: TRFAttachment) =>
            row.uploaded_at ? new Date(row.uploaded_at).toLocaleString() : '-'
          }
        />
        <Column
          header=""
          body={(row: TRFAttachment) => (
            <div className="flex gap-1">
              <Button
                icon="pi pi-download"
                text
                size="small"
                loading={downloadingId === row.id}
                onClick={() => handleDownload(row)}
                aria-label={`Download ${row.original_filename}`}
              />
              {canDelete(row) && (
                <Button
                  icon="pi pi-trash"
                  text
                  size="small"
                  severity="danger"
                  onClick={() => setDeleting(row)}
                  aria-label={`Remove ${row.original_filename}`}
                />
              )}
            </div>
          )}
        />
      </DataTable>

      <Dialog
        header="Remove Attachment"
        visible={deleting != null}
        onHide={() => setDeleting(null)}
        style={{ width: '460px' }}
        modal
      >
        <div className="flex flex-column gap-3">
          <p className="text-sm text-600 m-0">
            Remove <span className="font-medium">{deleting?.original_filename}</span>? The file and
            its metadata are deleted; the removal is recorded in the audit trail.
          </p>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Reason (optional)</label>
            <InputText
              value={deleteReason}
              onChange={(e) => setDeleteReason(e.target.value)}
              className="w-full"
              placeholder="e.g. Wrong injection attached"
            />
          </div>
          <Button
            label="Remove"
            severity="danger"
            onClick={handleDelete}
            loading={remove.isPending}
          />
        </div>
      </Dialog>
    </div>
  );
};

function fileIcon(contentType: string): string {
  if (contentType === 'application/pdf') return 'pi pi-file-pdf text-red-500';
  if (contentType.startsWith('image/')) return 'pi pi-image text-blue-500';
  if (contentType === 'text/csv') return 'pi pi-file-excel text-green-600';
  return 'pi pi-file text-500';
}
