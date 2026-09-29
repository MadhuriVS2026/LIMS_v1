/**
 * Column Management page — chromatography columns.
 */
import { useState } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column as PColumn } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputNumber } from 'primereact/inputnumber';
import { Dropdown } from 'primereact/dropdown';
import { StatusBadge } from '@shared/components/StatusBadge';
import { toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useColumns, useCreateColumn } from '../hooks/useResources';
import type { ColumnMaster } from '../models/resource.types';

const TYPES = ['C18', 'C8', 'HILIC', 'Phenyl', 'CN'];

export const ColumnsPage = () => {
  const { data: columns = [], isLoading } = useColumns();
  const createColumn = useCreateColumn();
  const { hasRole } = usePermissions();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<Partial<ColumnMaster>>({});

  const handleCreate = () => {
    if (!form.code || !form.name) {
      toastService.warn('Code and Name are required.', 'Missing fields');
      return;
    }
    createColumn.mutate(form, {
      onSuccess: (column) => {
        toastService.success(`Column ${column.code} added.`, 'Column Added');
        setShowModal(false);
        setForm({});
      },
    });
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{columns.length} columns</p>
        {hasRole('Admin') && <Button label="Add Column" icon="pi pi-plus" onClick={() => setShowModal(true)} />}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={columns} loading={isLoading} paginator rows={10} size="small">
          <PColumn field="code" header="Code" />
          <PColumn field="name" header="Name" />
          <PColumn field="type" header="Type" />
          <PColumn field="dimensions" header="Dimensions" />
          <PColumn header="Injections" body={(row) => `${row.current_injections}${row.max_injections ? '/' + row.max_injections : ''}`} />
          <PColumn header="Status" body={(row) => <StatusBadge status={row.status} />} />
        </DataTable>
      </div>

      <Dialog header="Add Column" visible={showModal} onHide={() => setShowModal(false)} style={{ width: '440px' }} modal>
        <div className="flex flex-column gap-3">
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Code</label><InputText value={form.code || ''} onChange={(e) => setForm({ ...form, code: e.target.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Name</label><InputText value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full" /></div>
          </div>
          <div className="grid">
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">Type</label><Dropdown value={form.type} options={TYPES} onChange={(e) => setForm({ ...form, type: e.value })} className="w-full" /></div>
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">Dimensions</label><InputText value={form.dimensions || ''} onChange={(e) => setForm({ ...form, dimensions: e.target.value })} className="w-full" placeholder="250x4.6mm, 5um" /></div>
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">Max Injections</label><InputNumber value={form.max_injections} onValueChange={(e) => setForm({ ...form, max_injections: e.value ?? undefined })} className="w-full" /></div>
          </div>
          <Button label="Add Column" onClick={handleCreate} loading={createColumn.isPending} className="w-full mt-1" />
        </div>
      </Dialog>
    </div>
  );
};
