/**
 * Worksheet panel for one TRF test line, for embedding in `TRFDetailPage`.
 *
 * Three states:
 *   1. no worksheet, Active templates exist → a template picker
 *   2. no worksheet, no Active templates     → nothing (the line keeps the
 *      existing free-text result path, which is why templating is additive
 *      rather than a replacement)
 *   3. a worksheet exists                    → the entry form plus Confirm
 *
 * Whether the form is editable and who may confirm is the backend's decision;
 * this component mirrors it so the UI does not offer an action that will 403.
 */
import { useState } from 'react';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { Dropdown } from 'primereact/dropdown';
import { InputTextarea } from 'primereact/inputtextarea';
import { Message } from 'primereact/message';
import { StatusBadge } from '@shared/components/StatusBadge';
import { getErrorMessage, toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useTemplatesForTest } from '../hooks/useTestTemplates';
import {
  useConfirmWorksheet,
  useCreateWorksheet,
  useSaveWorksheetValues,
  useWorksheetForLine,
} from '../hooks/useWorksheet';
import { WorksheetForm } from './WorksheetForm';
import type { WorksheetRow } from '../models/testTemplate.types';

interface TestLineWorksheetPanelProps {
  trfId: number;
  trfStatus: string;
  lineId: number;
  testId: number;
}

/** Mirrors `TestWorksheet.edit_mode_for` on the backend. */
type EditMode = 'Entry' | 'Correction' | null;

function editModeFor(trfStatus: string): EditMode {
  if (trfStatus === 'InProgress') return 'Entry';
  if (trfStatus === 'PendingADGLRelease') return 'Correction';
  return null;
}

export const TestLineWorksheetPanel = ({
  trfId,
  trfStatus,
  lineId,
  testId,
}: TestLineWorksheetPanelProps) => {
  const { hasRole } = usePermissions();
  const { data: detail, isLoading } = useWorksheetForLine(lineId);
  const { data: templates = [] } = useTemplatesForTest(testId);

  const createWorksheet = useCreateWorksheet();
  const saveValues = useSaveWorksheetValues();
  const confirmWorksheet = useConfirmWorksheet();

  const [pickedTemplateId, setPickedTemplateId] = useState<number | null>(null);
  const [showReason, setShowReason] = useState(false);
  const [reason, setReason] = useState('');
  const [pending, setPending] = useState<{
    context_values: Record<string, unknown>;
    group_values: Record<string, WorksheetRow[]>;
  } | null>(null);

  const mode = editModeFor(trfStatus);
  const canEnter = mode === 'Entry' && hasRole('Analyst', 'Admin');
  const canCorrect = mode === 'Correction' && hasRole('QA', 'Admin');
  const editable = canEnter || canCorrect;
  const canConfirm = canEnter;

  //  With one Active template there is no choice to make, so don't stage one as
  //  if there were. Only a genuine ambiguity should require a selection.
  const templateId = pickedTemplateId ?? (templates.length === 1 ? templates[0].id : null);

  if (isLoading) return <p className="text-sm text-500 m-0">Loading worksheet…</p>;

  // ── No worksheet yet ──
  if (!detail) {
    if (templates.length === 0) {
      return (
        <p className="text-sm text-500 m-0">
          No approved calculation template exists for this test. Enter the result as free text.
        </p>
      );
    }
    if (!canEnter) {
      return (
        <p className="text-sm text-500 m-0">
          {templates.length} calculation template(s) available. A worksheet can be started once the
          TRF is In Progress.
        </p>
      );
    }
    return (
      <div className="flex align-items-end gap-2 flex-wrap">
        {templates.length === 1 ? (
          <div>
            <span className="block text-xs text-500 mb-1">Calculation template</span>
            <span className="text-sm font-medium">
              {templates[0].name}{' '}
              <span className="font-mono text-500">
                {templates[0].code} v{templates[0].version}
              </span>
            </span>
          </div>
        ) : (
          <div>
            <label className="block text-xs text-500 mb-1">Calculation template</label>
            <Dropdown
              value={templateId}
              options={templates.map((t) => ({
                label: `${t.name} — ${t.code} v${t.version}`,
                value: t.id,
              }))}
              onChange={(e) => setPickedTemplateId(e.value)}
              placeholder="Select template..."
              className="w-22rem"
              aria-label="Calculation template"
            />
          </div>
        )}
        <Button
          label="Open Worksheet"
          icon="pi pi-table"
          disabled={templateId == null}
          loading={createWorksheet.isPending}
          onClick={() =>
            createWorksheet.mutate(
              { lineId, trfId, payload: { template_id: templateId as number } },
              {
                onSuccess: () => toastService.success('Worksheet created.', 'Worksheet'),
                onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Open Worksheet'),
              },
            )
          }
        />
      </div>
    );
  }

  // ── Worksheet exists ──
  const doSave = (
    payload: { context_values: Record<string, unknown>; group_values: Record<string, WorksheetRow[]> },
    withReason?: string,
  ) =>
    saveValues.mutate(
      { worksheetId: detail.worksheet.id, lineId, trfId, payload: { ...payload, reason: withReason } },
      {
        onSuccess: () => {
          setShowReason(false);
          setReason('');
          setPending(null);
          toastService.success('Worksheet saved.', 'Saved');
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Save Worksheet'),
      },
    );

  const handleSave = (payload: {
    context_values: Record<string, unknown>;
    group_values: Record<string, WorksheetRow[]>;
  }) => {
    //  A correction rewrites a result an analyst already submitted, so the
    //  backend requires a reason. Ask for it here rather than letting the save
    //  fail with a 400 the analyst has to decode.
    if (canCorrect) {
      setPending(payload);
      setShowReason(true);
      return;
    }
    doSave(payload);
  };

  const handleConfirm = () =>
    confirmWorksheet.mutate(
      { worksheetId: detail.worksheet.id, lineId, trfId },
      {
        onSuccess: (data) =>
          toastService.success(
            `Result ${data.test_line_result ?? ''} published to the test line.`,
            'Result Confirmed',
          ),
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Confirm Result'),
      },
    );

  return (
    <div className="flex flex-column gap-3">
      <div className="flex justify-content-between align-items-center flex-wrap gap-2">
        <div className="flex align-items-center gap-2">
          <span className="font-mono text-blue-600 text-sm">{detail.worksheet.template_code}</span>
          <span className="text-500 text-sm">v{detail.worksheet.template_version}</span>
          <span className="text-500 text-sm">·</span>
          <span className="text-sm">{detail.worksheet.template_name}</span>
          <StatusBadge status={detail.worksheet.status} />
        </div>

        {canConfirm && (
          <Button
            label={detail.worksheet.status === 'Confirmed' ? 'Re-confirm Result' : 'Confirm Result'}
            icon="pi pi-check"
            severity="success"
            loading={confirmWorksheet.isPending}
            disabled={detail.computed.has_blocking_failure}
            onClick={handleConfirm}
          />
        )}
      </div>

      {detail.worksheet.status === 'Confirmed' && (
        <Message
          severity="success"
          text={`Confirmed by ${detail.worksheet.confirmed_by} — result ${detail.worksheet.reportable_result} is on the test line.`}
        />
      )}
      {canCorrect && (
        <Message
          severity="info"
          text="Correction mode: changes are recorded against your user with a mandatory reason, and the result must be re-confirmed by the analyst."
        />
      )}
      {!editable && mode === null && (
        <Message
          severity="info"
          text={`The worksheet is read-only while the TRF is ${trfStatus}.`}
        />
      )}

      <WorksheetForm
        detail={detail}
        editable={editable}
        saving={saveValues.isPending}
        onSave={handleSave}
      />

      <Dialog
        header="Reason for Correction"
        visible={showReason}
        onHide={() => setShowReason(false)}
        style={{ width: '460px' }}
        modal
      >
        <div className="flex flex-column gap-3">
          <p className="text-sm text-600 m-0">
            This worksheet already carries a submitted result. The reason is written to the audit
            trail alongside the changed values.
          </p>
          <InputTextarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="w-full"
            placeholder="e.g. Area transposed from the wrong chromatogram"
            autoFocus
          />
          <Button
            label="Save Correction"
            onClick={() => pending && doSave(pending, reason.trim())}
            loading={saveValues.isPending}
            disabled={!reason.trim()}
          />
        </div>
      </Dialog>
    </div>
  );
};
