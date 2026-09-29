/**
 * Test template detail — header, JSON definition editor, version history and
 * the lifecycle actions.
 *
 * The definition is only editable while `Draft`. Editing an approved template
 * means branching a new version, which leaves the approved one byte-identical so
 * every worksheet already run against it stays reproducible.
 */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { Column } from 'primereact/column';
import { DataTable } from 'primereact/datatable';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Message } from 'primereact/message';
import { ESignDialog } from '@shared/components/ESignDialog';
import { StatusBadge } from '@shared/components/StatusBadge';
import { getErrorMessage, toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import {
  useApproveTemplate,
  useDeactivateTemplate,
  useNewTemplateVersion,
  useRejectTemplate,
  useSubmitTemplate,
  useTemplateDetail,
  useTemplateVersions,
  useUpdateTemplateDefinition,
  useUpdateTemplateHeader,
} from '../hooks/useTestTemplates';
import { describeDefinition } from '../models/describeDefinition';
import type { TestTemplateSummary } from '../models/testTemplate.types';

export const TemplateDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const templateId = id ? Number(id) : undefined;
  const navigate = useNavigate();
  const { hasRole } = usePermissions();

  const isAdmin = hasRole('Admin');
  const isReviewer = hasRole('Admin', 'Supervisor', 'QA');

  const { data: template, isLoading } = useTemplateDetail(templateId);
  const { data: versions = [] } = useTemplateVersions(templateId);

  const updateDefinition = useUpdateTemplateDefinition();
  const updateHeader = useUpdateTemplateHeader();
  const submit = useSubmitTemplate();
  const approve = useApproveTemplate();
  const reject = useRejectTemplate();
  const newVersion = useNewTemplateVersion();
  const deactivate = useDeactivateTemplate();

  const [draftJson, setDraftJson] = useState('');
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [showEsign, setShowEsign] = useState(false);
  const [showReject, setShowReject] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [name, setName] = useState('');
  const [resultUnit, setResultUnit] = useState('');

  //  Reset local editor state whenever a different template (or version) loads,
  //  so a stale draft can never be saved onto the wrong record.
  useEffect(() => {
    if (!template) return;
    setDraftJson(JSON.stringify(template.definition ?? {}, null, 2));
    setJsonError(null);
    setName(template.name);
    setResultUnit(template.result_unit ?? '');
  }, [template?.id, template?.modified_date]);

  const isDraft = template?.status === 'Draft';
  const canEdit = isAdmin && isDraft;

  const summary = useMemo(
    () => (template ? describeDefinition(template.definition) : null),
    [template],
  );

  //  Live parse feedback as the author types — a syntax error is theirs to see
  //  immediately, not on a round trip.
  const handleJsonChange = (value: string) => {
    setDraftJson(value);
    try {
      JSON.parse(value);
      setJsonError(null);
    } catch (e) {
      setJsonError((e as Error).message);
    }
  };

  if (isLoading) return <p className="text-500">Loading template...</p>;
  if (!template || templateId == null) return <Message severity="warn" text="Template not found." />;

  const handleSaveDefinition = () => {
    let definition: Record<string, unknown>;
    try {
      definition = JSON.parse(draftJson);
    } catch (e) {
      toastService.error((e as Error).message, 'Definition Is Not Valid JSON');
      return;
    }
    updateDefinition.mutate(
      { id: templateId, payload: { definition } },
      {
        onSuccess: () => toastService.success('Definition saved.', 'Template Updated'),
        onError: (e) => toastService.error(getErrorMessage(e), 'Definition Rejected'),
      },
    );
  };

  const handleSaveHeader = () => {
    updateHeader.mutate(
      { id: templateId, payload: { name: name.trim(), result_unit: resultUnit.trim() || null } },
      {
        onSuccess: () => toastService.success('Template updated.', 'Saved'),
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Save'),
      },
    );
  };

  const handleSubmit = () =>
    submit.mutate(templateId, {
      onSuccess: () => toastService.success('Sent for approval.', 'Submitted'),
      onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Submit'),
    });

  const handleApprove = (password: string, comments?: string) =>
    approve.mutate(
      { id: templateId, payload: { password, comments } },
      {
        onSuccess: (t) => {
          setShowEsign(false);
          toastService.success(`${t.code} v${t.version} is now Active.`, 'Approved');
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Approval Failed'),
      },
    );

  const handleReject = () => {
    if (!rejectReason.trim()) {
      toastService.warn('A reason is required.', 'Missing Reason');
      return;
    }
    reject.mutate(
      { id: templateId, reason: rejectReason.trim() },
      {
        onSuccess: () => {
          setShowReject(false);
          setRejectReason('');
          toastService.success('Returned to Draft.', 'Rejected');
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Reject'),
      },
    );
  };

  const handleNewVersion = () =>
    newVersion.mutate(templateId, {
      onSuccess: (t) => {
        toastService.success(`Draft v${t.version} created.`, 'New Version');
        navigate(`/test-templates/${t.id}`);
      },
      onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Create Version'),
    });

  const handleDeactivate = () =>
    deactivate.mutate(
      { id: templateId, reason: null },
      {
        onSuccess: () => toastService.success('Template deactivated.', 'Inactive'),
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Deactivate'),
      },
    );

  return (
    <div className="flex flex-column gap-3">
      <div className="flex justify-content-between align-items-start flex-wrap gap-2">
        <div>
          <Button
            label="Back to Templates"
            icon="pi pi-arrow-left"
            text
            size="small"
            onClick={() => navigate('/test-templates')}
          />
          <div className="flex align-items-center gap-3 mt-1">
            <h2 className="m-0 text-xl">
              <span className="font-mono text-blue-600">{template.code}</span>{' '}
              <span className="text-500 font-normal">v{template.version}</span>
            </h2>
            <StatusBadge status={template.status} />
          </div>
          <p className="text-sm text-500 m-0 mt-1">
            {template.name} · archetype {template.archetype}
            {template.test_name ? ` · ${template.test_name} (${template.test_code})` : ''}
          </p>
        </div>

        <div className="flex gap-2 flex-wrap">
          {isAdmin && isDraft && (
            <Button label="Submit for Approval" icon="pi pi-send" onClick={handleSubmit} loading={submit.isPending} />
          )}
          {isReviewer && template.status === 'PendingApproval' && (
            <>
              <Button
                label="Approve"
                icon="pi pi-check"
                severity="success"
                onClick={() => setShowEsign(true)}
              />
              <Button
                label="Reject"
                icon="pi pi-times"
                severity="danger"
                outlined
                onClick={() => setShowReject(true)}
              />
            </>
          )}
          {isAdmin && (template.status === 'Active' || template.status === 'Inactive') && (
            <Button
              label="New Version"
              icon="pi pi-copy"
              outlined
              onClick={handleNewVersion}
              loading={newVersion.isPending}
            />
          )}
          {isAdmin && template.status === 'Active' && (
            <Button
              label="Deactivate"
              icon="pi pi-ban"
              severity="secondary"
              outlined
              onClick={handleDeactivate}
              loading={deactivate.isPending}
            />
          )}
        </div>
      </div>

      {template.status === 'Active' && (
        <Message
          severity="info"
          text="This version is in force. Its definition is locked — use New Version to change it, which leaves worksheets already run against this version untouched."
        />
      )}
      {template.superseded_by_id != null && (
        <Message
          severity="warn"
          text="A newer version has superseded this one. It stays available so existing worksheets remain reproducible."
        />
      )}

      <div className="grid">
        <div className="col-12 lg:col-8">
          <Card title="Definition">
            {canEdit ? (
              <div className="flex flex-column gap-2">
                <InputTextarea
                  value={draftJson}
                  onChange={(e) => handleJsonChange(e.target.value)}
                  rows={28}
                  className="w-full font-mono text-sm"
                  spellCheck={false}
                  aria-label="Template definition JSON"
                />
                {jsonError ? (
                  <Message severity="error" text={`JSON: ${jsonError}`} />
                ) : (
                  <small className="text-500">
                    Valid JSON. The server additionally checks the dependency graph, so a circular
                    reference or unknown function is rejected on save.
                  </small>
                )}
                <div className="flex gap-2">
                  <Button
                    label="Save Definition"
                    icon="pi pi-save"
                    onClick={handleSaveDefinition}
                    loading={updateDefinition.isPending}
                    disabled={jsonError != null}
                  />
                  <Button
                    label="Revert"
                    text
                    onClick={() => handleJsonChange(JSON.stringify(template.definition ?? {}, null, 2))}
                  />
                </div>
              </div>
            ) : (
              <pre
                className="font-mono text-sm bg-gray-50 border-1 border-200 border-round p-3 m-0 overflow-auto"
                style={{ maxHeight: '40rem' }}
              >
                {JSON.stringify(template.definition ?? {}, null, 2)}
              </pre>
            )}
          </Card>
        </div>

        <div className="col-12 lg:col-4 flex flex-column gap-3">
          <Card title="Summary">
            {summary && (
              <ul className="list-none p-0 m-0 flex flex-column gap-2 text-sm">
                <li>
                  <span className="text-500">Context fields</span>
                  <span className="float-right font-medium">{summary.contextCount}</span>
                </li>
                <li>
                  <span className="text-500">Groups</span>
                  <span className="float-right font-medium">{summary.groupCount}</span>
                </li>
                <li>
                  <span className="text-500">Analyst inputs</span>
                  <span className="float-right font-medium">{summary.inputCount}</span>
                </li>
                <li>
                  <span className="text-500">Area fields</span>
                  <span className="float-right font-medium">{summary.areaCount}</span>
                </li>
                <li>
                  <span className="text-500">Calculated fields</span>
                  <span className="float-right font-medium">{summary.calculatedCount}</span>
                </li>
                <li>
                  <span className="text-500">Acceptance criteria</span>
                  <span className="float-right font-medium">
                    {summary.criteriaCount}
                    {summary.blockingCriteriaCount > 0
                      ? ` (${summary.blockingCriteriaCount} blocking)`
                      : ''}
                  </span>
                </li>
                <li>
                  <span className="text-500">Reportable result</span>
                  <span className="float-right font-mono">{summary.resultRef ?? 'not set'}</span>
                </li>
              </ul>
            )}
            {summary && !summary.resultRef && (
              <Message
                className="mt-3"
                severity="warn"
                text="No resultRef — a worksheet from this template cannot publish a result to its test line."
              />
            )}
            {summary && summary.areaCount > 0 && (
              <p className="text-xs text-500 mt-3 mb-0">
                Area fields are entered manually today. The Waters CDS integration will populate them
                directly without any change to this definition.
              </p>
            )}
          </Card>

          {canEdit && (
            <Card title="Header">
              <div className="flex flex-column gap-2">
                <div>
                  <label className="block text-sm font-medium text-700 mb-1">Name</label>
                  <InputText value={name} onChange={(e) => setName(e.target.value)} className="w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-700 mb-1">Result Unit</label>
                  <InputText
                    value={resultUnit}
                    onChange={(e) => setResultUnit(e.target.value)}
                    className="w-full"
                  />
                </div>
                <Button
                  label="Save Header"
                  onClick={handleSaveHeader}
                  loading={updateHeader.isPending}
                  outlined
                />
              </div>
            </Card>
          )}

          <Card title="Version History">
            <DataTable value={versions} size="small" emptyMessage="No versions." className="text-sm">
              <Column
                header="Version"
                body={(row: TestTemplateSummary) => (
                  <Button
                    label={`v${row.version}`}
                    text
                    size="small"
                    className="p-0"
                    onClick={() => navigate(`/test-templates/${row.id}`)}
                  />
                )}
              />
              <Column header="Status" body={(row: TestTemplateSummary) => <StatusBadge status={row.status} />} />
              <Column header="Approved By" body={(row: TestTemplateSummary) => row.approved_by || '-'} />
            </DataTable>
          </Card>
        </div>
      </div>

      <ESignDialog
        visible={showEsign}
        title="Approve Test Template"
        actionLabel="Sign & Approve"
        loading={approve.isPending}
        onHide={() => setShowEsign(false)}
        onConfirm={handleApprove}
      />

      <Dialog
        header="Reject Template"
        visible={showReject}
        onHide={() => setShowReject(false)}
        style={{ width: '440px' }}
        modal
      >
        <div className="flex flex-column gap-3">
          <p className="text-sm text-600 m-0">
            The template returns to Draft so its author can revise it.
          </p>
          <InputTextarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            rows={3}
            className="w-full"
            placeholder="Reason for rejection"
            autoFocus
          />
          <Button
            label="Reject"
            severity="danger"
            onClick={handleReject}
            loading={reject.isPending}
            disabled={!rejectReason.trim()}
          />
        </div>
      </Dialog>
    </div>
  );
};
