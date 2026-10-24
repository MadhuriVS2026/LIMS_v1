/**
 * Project Master page (Resource Manager).
 * Lists R&D / DLIMS projects with all 17 fields; Admin-gated Add Project dialog.
 */
import { useState } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { Calendar } from 'primereact/calendar';
import { StatusBadge } from '@shared/components/StatusBadge';
import { toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useCreateProject, useProjects } from '../hooks/useResources';
import type { ProjectMaster } from '../models/resource.types';

const STATUS_OPTIONS = ['Active', 'Inactive'];

export const ProjectMasterPage = () => {
  const { data: projects = [], isLoading } = useProjects();
  const createProject = useCreateProject();
  const { hasRole } = usePermissions();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<Partial<ProjectMaster>>({ status: 'Active' });

  const handleCreate = () => {
    if (!form.project_id || !form.product_name) {
      toastService.warn('Project ID and Product Name are required.', 'Missing fields');
      return;
    }
    createProject.mutate(form, {
      onSuccess: (project) => {
        toastService.success(`Project ${project.project_id} added.`, 'Project Added');
        setShowModal(false);
        setForm({ status: 'Active' });
      },
    });
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{projects.length} projects</p>
        {hasRole('Admin') && <Button label="Add Project" icon="pi pi-plus" onClick={() => setShowModal(true)} />}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={projects} loading={isLoading} paginator rows={10} size="small">
          <Column header="Sr No" body={(_row, { rowIndex }) => rowIndex + 1} />
          <Column field="project_id" header="Project ID" />
          <Column field="product_name" header="Product Name" />
          <Column field="product_code" header="Product Code" />
          <Column field="project_code" header="Project Code" />
          <Column field="group_lead" header="Group Lead" />
          <Column field="location" header="Location" />
          <Column field="market" header="Market" />
          <Column header="Start Date" body={(row) => (row.start_date ? new Date(row.start_date).toLocaleDateString() : '-')} />
          <Column header="End Date" body={(row) => (row.end_date ? new Date(row.end_date).toLocaleDateString() : '-')} />
          <Column field="license" header="License" />
          <Column header="Status" body={(row) => <StatusBadge status={row.status} />} />
        </DataTable>
      </div>

      <Dialog header="Add Project" visible={showModal} onHide={() => setShowModal(false)} style={{ width: '640px' }} modal>
        <div className="flex flex-column gap-3">
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Project ID</label><InputText value={form.project_id || ''} onChange={(e) => setForm({ ...form, project_id: e.target.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Product Name</label><InputText value={form.product_name || ''} onChange={(e) => setForm({ ...form, product_name: e.target.value })} className="w-full" /></div>
          </div>
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Product Code</label><InputText value={form.product_code || ''} onChange={(e) => setForm({ ...form, product_code: e.target.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Project Code</label><InputText value={form.project_code || ''} onChange={(e) => setForm({ ...form, project_code: e.target.value })} className="w-full" /></div>
          </div>
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Project Code (Academic Research)</label><InputText value={form.project_code_academic || ''} onChange={(e) => setForm({ ...form, project_code_academic: e.target.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">BD Code (SAP)</label><InputText value={form.bd_code_sap || ''} onChange={(e) => setForm({ ...form, bd_code_sap: e.target.value })} className="w-full" /></div>
          </div>
          <div className="grid">
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">Group Lead</label><InputText value={form.group_lead || ''} onChange={(e) => setForm({ ...form, group_lead: e.target.value })} className="w-full" /></div>
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">Location</label><InputText value={form.location || ''} onChange={(e) => setForm({ ...form, location: e.target.value })} className="w-full" /></div>
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">Market</label><InputText value={form.market || ''} onChange={(e) => setForm({ ...form, market: e.target.value })} className="w-full" /></div>
          </div>
          <div className="grid">
            <div className="col-4">
              <label className="block text-sm font-medium text-700 mb-1">Start Date</label>
              <Calendar
                value={form.start_date ? new Date(form.start_date) : null}
                onChange={(e) => setForm({ ...form, start_date: e.value ? (e.value as Date).toISOString() : undefined })}
                className="w-full"
                dateFormat="dd-M-yy"
              />
            </div>
            <div className="col-4">
              <label className="block text-sm font-medium text-700 mb-1">End Date</label>
              <Calendar
                value={form.end_date ? new Date(form.end_date) : null}
                onChange={(e) => setForm({ ...form, end_date: e.value ? (e.value as Date).toISOString() : undefined })}
                className="w-full"
                dateFormat="dd-M-yy"
              />
            </div>
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">License</label><InputText value={form.license || ''} onChange={(e) => setForm({ ...form, license: e.target.value })} className="w-full" /></div>
          </div>
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Project Status</label><Dropdown value={form.status} options={STATUS_OPTIONS} onChange={(e) => setForm({ ...form, status: e.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Requested person/Remark</label><InputText value={form.requested_person || ''} onChange={(e) => setForm({ ...form, requested_person: e.target.value })} className="w-full" /></div>
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Comments</label>
            <InputTextarea value={form.comments || ''} onChange={(e) => setForm({ ...form, comments: e.target.value })} rows={2} className="w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Remarks</label>
            <InputTextarea value={form.remarks || ''} onChange={(e) => setForm({ ...form, remarks: e.target.value })} rows={2} className="w-full" />
          </div>
          <Button label="Add Project" onClick={handleCreate} loading={createProject.isPending} className="w-full mt-1" />
        </div>
      </Dialog>
    </div>
  );
};
