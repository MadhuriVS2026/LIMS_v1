/**
 * ARD-EXP-TEMPLATES Master page (Resource Manager — Admin).
 * Table view of ARD experiment templates with Admin-gated Add / Edit / Delete.
 * Columns: Sr No, Template Name, Comments, Primary Department Name, Plant,
 * Location, Is active, Action (edit/delete), Secondary Dept, Module.
 */
import { useState } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { InputSwitch } from 'primereact/inputswitch';
import { Tag } from 'primereact/tag';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import {
  useARDExpTemplates,
  useCreateARDExpTemplate,
  useDeleteARDExpTemplate,
  useUpdateARDExpTemplate,
} from '../hooks/useResources';
import type { ARDExpTemplate } from '../models/resource.types';
import { ADSSheetViewer } from '../components/ADSSheetViewer';

type TemplateForm = Partial<ARDExpTemplate>;

const EMPTY_FORM: TemplateForm = { is_active: true };

export const ARDExpTemplatesPage = () => {
  const { data: templates = [], isLoading } = useARDExpTemplates();
  const createTemplate = useCreateARDExpTemplate();
  const updateTemplate = useUpdateARDExpTemplate();
  const deleteTemplate = useDeleteARDExpTemplate();
  const { hasRole } = usePermissions();
  const isAdmin = hasRole('Admin');

  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<TemplateForm>(EMPTY_FORM);
  const [viewing, setViewing] = useState<ARDExpTemplate | null>(null);

  const openAdd = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setShowModal(true);
  };

  const openEdit = (row: ARDExpTemplate) => {
    setEditingId(row.id);
    setForm({ ...row });
    setShowModal(true);
  };

  const handleSave = () => {
    if (!form.template_name?.trim()) {
      toastService.warn('Template Name is required.', 'Missing fields');
      return;
    }
    const payload: TemplateForm = {
      template_name: form.template_name,
      comments: form.comments ?? null,
      primary_department: form.primary_department ?? null,
      plant: form.plant ?? null,
      location: form.location ?? null,
      is_active: form.is_active ?? true,
      secondary_department: form.secondary_department ?? null,
      module: form.module ?? null,
    };

    if (editingId != null) {
      updateTemplate.mutate(
        { id: editingId, payload },
        {
          onSuccess: (tpl) => {
            toastService.success(`Template "${tpl.template_name}" updated.`, 'Template Updated');
            setShowModal(false);
            setForm(EMPTY_FORM);
            setEditingId(null);
          },
        },
      );
    } else {
      createTemplate.mutate(payload, {
        onSuccess: (tpl) => {
          toastService.success(`Template "${tpl.template_name}" added.`, 'Template Added');
          setShowModal(false);
          setForm(EMPTY_FORM);
        },
      });
    }
  };

  const confirmDelete = (row: ARDExpTemplate) => {
    confirmDialog({
      message: `Delete template "${row.template_name}"? This cannot be undone.`,
      header: 'Delete Template',
      icon: 'pi pi-exclamation-triangle',
      acceptClassName: 'p-button-danger',
      accept: () =>
        deleteTemplate.mutate(row.id, {
          onSuccess: () => toastService.success(`Template "${row.template_name}" deleted.`, 'Template Deleted'),
        }),
    });
  };

  const actionBody = (row: ARDExpTemplate) => (
    <div className="flex gap-1">
      <Button
        icon="pi pi-eye"
        rounded
        text
        severity="info"
        size="small"
        aria-label="View full sheet"
        tooltip="View full sheet"
        onClick={() => setViewing(row)}
      />
      {isAdmin && (
        <>
          <Button
            icon="pi pi-pencil"
            rounded
            text
            severity="secondary"
            size="small"
            aria-label="Edit template"
            onClick={() => openEdit(row)}
          />
          <Button
            icon="pi pi-trash"
            rounded
            text
            severity="danger"
            size="small"
            aria-label="Delete template"
            onClick={() => confirmDelete(row)}
          />
        </>
      )}
    </div>
  );

  return (
    <div>
      <ConfirmDialog />

      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{templates.length} templates</p>
        {isAdmin && <Button label="Add Template" icon="pi pi-plus" onClick={openAdd} />}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={templates} loading={isLoading} paginator rows={10} size="small">
          <Column header="Sr No" body={(_row, { rowIndex }) => rowIndex + 1} style={{ width: '70px' }} />
          <Column field="template_name" header="Template Name" />
          <Column field="comments" header="Comments" body={(row) => row.comments || '-'} />
          <Column field="primary_department" header="Primary Department Name" body={(row) => row.primary_department || '-'} />
          <Column field="plant" header="Plant" body={(row) => row.plant || '-'} />
          <Column field="location" header="Location" body={(row) => row.location || '-'} />
          <Column
            header="Is active"
            body={(row) => (
              <Tag value={row.is_active ? 'Active' : 'Inactive'} severity={row.is_active ? 'success' : 'danger'} />
            )}
          />
          <Column header="Action" body={actionBody} style={{ width: '150px' }} />
          <Column field="template_code" header="Template Code" body={(row) => row.template_code || '-'} />
          <Column field="secondary_department" header="Secondary Dept" body={(row) => row.secondary_department || '-'} />
          <Column field="module" header="Module" body={(row) => row.module || '-'} />
        </DataTable>
      </div>

      <Dialog
        header={editingId != null ? 'Edit Template' : 'Add Template'}
        visible={showModal}
        onHide={() => setShowModal(false)}
        style={{ width: '640px' }}
        modal
      >
        <div className="flex flex-column gap-3">
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Template Name</label>
            <InputText
              value={form.template_name || ''}
              onChange={(e) => setForm({ ...form, template_name: e.target.value })}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Comments</label>
            <InputTextarea
              value={form.comments || ''}
              onChange={(e) => setForm({ ...form, comments: e.target.value })}
              rows={2}
              className="w-full"
            />
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Primary Department Name</label>
              <InputText
                value={form.primary_department || ''}
                onChange={(e) => setForm({ ...form, primary_department: e.target.value })}
                className="w-full"
              />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Secondary Dept</label>
              <InputText
                value={form.secondary_department || ''}
                onChange={(e) => setForm({ ...form, secondary_department: e.target.value })}
                className="w-full"
              />
            </div>
          </div>
          <div className="grid">
            <div className="col-4">
              <label className="block text-sm font-medium text-700 mb-1">Plant</label>
              <InputText
                value={form.plant || ''}
                onChange={(e) => setForm({ ...form, plant: e.target.value })}
                className="w-full"
              />
            </div>
            <div className="col-4">
              <label className="block text-sm font-medium text-700 mb-1">Location</label>
              <InputText
                value={form.location || ''}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
                className="w-full"
              />
            </div>
            <div className="col-4">
              <label className="block text-sm font-medium text-700 mb-1">Module</label>
              <InputText
                value={form.module || ''}
                onChange={(e) => setForm({ ...form, module: e.target.value })}
                className="w-full"
              />
            </div>
          </div>
          <div className="flex align-items-center gap-2">
            <InputSwitch
              checked={form.is_active ?? true}
              onChange={(e) => setForm({ ...form, is_active: e.value })}
            />
            <label className="text-sm font-medium text-700">Is active</label>
          </div>
          <Button
            label={editingId != null ? 'Save Changes' : 'Add Template'}
            onClick={handleSave}
            loading={createTemplate.isPending || updateTemplate.isPending}
            className="w-full mt-1"
          />
        </div>
      </Dialog>

      <Dialog
        header={viewing?.template_name || 'Template'}
        visible={viewing != null}
        onHide={() => setViewing(null)}
        style={{ width: '900px' }}
        maximizable
        modal
      >
        {viewing && <ADSSheetViewer content={viewing.content} />}
      </Dialog>
    </div>
  );
};
