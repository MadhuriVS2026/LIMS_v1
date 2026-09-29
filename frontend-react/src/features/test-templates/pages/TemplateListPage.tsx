/**
 * Test template list — the master-data catalogue of calculation sheets that
 * replace the lab's standalone Excel workbooks.
 *
 * Filters on archetype and status. "New Template" is Admin-only; a new template
 * starts as `Draft` and only becomes selectable on a TRF test line once it has
 * been approved.
 */
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dropdown } from 'primereact/dropdown';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { StatusBadge } from '@shared/components/StatusBadge';
import { getErrorMessage, toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useTests } from '@features/sample-management/hooks/useSamples';
import { useCreateTemplate, useTemplateList } from '../hooks/useTestTemplates';
import { ARCHETYPES, STARTER_DEFINITION } from '../models/archetypes';
import type { CreateTemplateRequest, TestTemplateSummary } from '../models/testTemplate.types';

const STATUS_OPTIONS = [
  { label: 'All', value: 'All' },
  { label: 'Draft', value: 'Draft' },
  { label: 'Pending Approval', value: 'PendingApproval' },
  { label: 'Active', value: 'Active' },
  { label: 'Inactive', value: 'Inactive' },
];

interface DraftForm {
  name: string;
  archetype: string;
  test_id?: number;
  result_unit: string;
  definition: string;
}

const emptyForm: DraftForm = {
  name: '',
  archetype: '',
  result_unit: '%',
  definition: JSON.stringify(STARTER_DEFINITION, null, 2),
};

export const TemplateListPage = () => {
  const navigate = useNavigate();
  const { hasRole } = usePermissions();
  const isAdmin = hasRole('Admin');

  const { data: templates = [], isLoading } = useTemplateList();
  const { data: tests = [] } = useTests();
  const createTemplate = useCreateTemplate();

  const [statusFilter, setStatusFilter] = useState('All');
  const [archetypeFilter, setArchetypeFilter] = useState('All');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<DraftForm>(emptyForm);

  const activeTests = tests.filter((t) => t.status === 'Active');

  const archetypeOptions = useMemo(
    () => [
      { label: 'All', value: 'All' },
      ...ARCHETYPES.map((a) => ({ label: `${a.code} — ${a.label}`, value: a.code })),
    ],
    [],
  );

  const filtered = useMemo(
    () =>
      templates.filter(
        (t) =>
          (statusFilter === 'All' || t.status === statusFilter) &&
          (archetypeFilter === 'All' || t.archetype === archetypeFilter),
      ),
    [templates, statusFilter, archetypeFilter],
  );

  const closeCreate = () => {
    setShowCreate(false);
    setForm(emptyForm);
  };

  const handleCreate = () => {
    if (!form.name.trim() || !form.archetype || form.test_id == null) {
      toastService.warn('Name, Archetype and Test are required.', 'Missing Fields');
      return;
    }

    //  Parse client-side first. A JSON syntax error is the analyst's typo, not a
    //  server condition, and a 400 round trip would lose the caret position.
    let definition: CreateTemplateRequest['definition'];
    try {
      definition = JSON.parse(form.definition);
    } catch (e) {
      toastService.error((e as Error).message, 'Definition Is Not Valid JSON');
      return;
    }

    createTemplate.mutate(
      {
        name: form.name.trim(),
        archetype: form.archetype,
        test_id: form.test_id,
        result_unit: form.result_unit.trim() || null,
        definition,
      },
      {
        onSuccess: (template) => {
          toastService.success(`${template.code} created as Draft.`, 'Template Created');
          closeCreate();
          navigate(`/test-templates/${template.id}`);
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Create Template'),
      },
    );
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <div className="flex align-items-center gap-3 flex-wrap">
          <p className="text-sm text-500 m-0">{filtered.length} template(s)</p>
          <Dropdown
            value={archetypeFilter}
            options={archetypeOptions}
            onChange={(e) => setArchetypeFilter(e.value)}
            className="w-18rem"
            aria-label="Filter by archetype"
          />
          <Dropdown
            value={statusFilter}
            options={STATUS_OPTIONS}
            onChange={(e) => setStatusFilter(e.value)}
            className="w-12rem"
            aria-label="Filter by status"
          />
        </div>
        {isAdmin && (
          <Button label="New Template" icon="pi pi-plus" onClick={() => setShowCreate(true)} />
        )}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable
          value={filtered}
          loading={isLoading}
          paginator
          rows={10}
          size="small"
          emptyMessage="No test templates found."
        >
          <Column
            field="code"
            header="Code"
            body={(row: TestTemplateSummary) => (
              <span className="font-mono text-blue-600">{row.code}</span>
            )}
          />
          <Column field="name" header="Name" />
          <Column field="archetype" header="Archetype" />
          <Column
            header="Test"
            body={(row: TestTemplateSummary) =>
              row.test_name ? `${row.test_name} (${row.test_code})` : '-'
            }
          />
          <Column
            header="Version"
            body={(row: TestTemplateSummary) => <span className="font-mono">v{row.version}</span>}
          />
          <Column
            header="Status"
            body={(row: TestTemplateSummary) => <StatusBadge status={row.status} />}
          />
          <Column
            header="Result Unit"
            body={(row: TestTemplateSummary) => row.result_unit || '-'}
          />
          <Column
            header="Approved By"
            body={(row: TestTemplateSummary) => row.approved_by || '-'}
          />
          <Column
            header="Actions"
            body={(row: TestTemplateSummary) => (
              <Button
                label="View"
                size="small"
                text
                onClick={() => navigate(`/test-templates/${row.id}`)}
              />
            )}
          />
        </DataTable>
      </div>

      <Dialog
        header="New Test Template"
        visible={showCreate}
        onHide={closeCreate}
        style={{ width: '760px' }}
        modal
      >
        <div className="flex flex-column gap-3">
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Name</label>
              <InputText
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full"
                placeholder="e.g. Assay by HPLC"
              />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Test</label>
              <Dropdown
                value={form.test_id}
                options={activeTests.map((t) => ({ label: `${t.name} (${t.code})`, value: t.id }))}
                onChange={(e) => setForm({ ...form, test_id: e.value })}
                placeholder="Select test..."
                className="w-full"
                filter
              />
            </div>
          </div>
          <div className="grid">
            <div className="col-8">
              <label className="block text-sm font-medium text-700 mb-1">Archetype</label>
              <Dropdown
                value={form.archetype}
                options={ARCHETYPES.map((a) => ({
                  label: `${a.code} — ${a.label}`,
                  value: a.code,
                }))}
                onChange={(e) => setForm({ ...form, archetype: e.value })}
                placeholder="Select archetype..."
                className="w-full"
              />
            </div>
            <div className="col-4">
              <label className="block text-sm font-medium text-700 mb-1">Result Unit</label>
              <InputText
                value={form.result_unit}
                onChange={(e) => setForm({ ...form, result_unit: e.target.value })}
                className="w-full"
                placeholder="e.g. %"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Definition (JSON)</label>
            <InputTextarea
              value={form.definition}
              onChange={(e) => setForm({ ...form, definition: e.target.value })}
              rows={16}
              className="w-full font-mono text-sm"
              spellCheck={false}
            />
            <small className="text-500">
              A starter skeleton is pre-filled. The definition is validated on save — a circular
              reference or an unknown function is rejected before the template is created.
            </small>
          </div>
          <Button
            label="Create Draft Template"
            onClick={handleCreate}
            loading={createTemplate.isPending}
            className="w-full mt-1"
          />
        </div>
      </Dialog>
    </div>
  );
};
