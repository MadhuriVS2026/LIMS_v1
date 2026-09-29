/**
 * Volumetric Solutions page — preparation & standardization tracking.
 */
import { useState } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputNumber } from 'primereact/inputnumber';
import { StatusBadge } from '@shared/components/StatusBadge';
import { toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useCreateVolumetricSolution, useVolumetricSolutions } from '../hooks/useResources';
import type { VolumetricSolution } from '../models/resource.types';

export const VolumetricPage = () => {
  const { data: solutions = [], isLoading } = useVolumetricSolutions();
  const createSolution = useCreateVolumetricSolution();
  const { hasRole } = usePermissions();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<Partial<VolumetricSolution>>({});

  const handleCreate = () => {
    if (!form.code || !form.name) {
      toastService.warn('Code and Name are required.', 'Missing fields');
      return;
    }
    createSolution.mutate(form, {
      onSuccess: (solution) => {
        toastService.success(`Volumetric solution ${solution.code} added.`, 'Solution Added');
        setShowModal(false);
        setForm({});
      },
    });
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{solutions.length} volumetric solutions</p>
        {hasRole('Admin', 'Analyst') && <Button label="Add Solution" icon="pi pi-plus" onClick={() => setShowModal(true)} />}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={solutions} loading={isLoading} paginator rows={10} size="small">
          <Column field="code" header="Code" />
          <Column field="name" header="Name" />
          <Column field="concentration" header="Concentration" />
          <Column field="standardization_factor" header="Factor" />
          <Column field="prepared_by" header="Prepared By" />
          <Column header="Expiry" body={(row) => (row.expiry_date ? new Date(row.expiry_date).toLocaleDateString() : '-')} />
          <Column header="Status" body={(row) => <StatusBadge status={row.status} />} />
        </DataTable>
      </div>

      <Dialog header="Add Volumetric Solution" visible={showModal} onHide={() => setShowModal(false)} style={{ width: '440px' }} modal>
        <div className="flex flex-column gap-3">
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Code</label><InputText value={form.code || ''} onChange={(e) => setForm({ ...form, code: e.target.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Name</label><InputText value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full" /></div>
          </div>
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Concentration</label><InputText value={form.concentration || ''} onChange={(e) => setForm({ ...form, concentration: e.target.value })} className="w-full" placeholder="e.g., 0.1N" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Standardization Factor</label><InputNumber value={form.standardization_factor} onValueChange={(e) => setForm({ ...form, standardization_factor: e.value ?? undefined })} mode="decimal" maxFractionDigits={4} className="w-full" /></div>
          </div>
          <Button label="Add Solution" onClick={handleCreate} loading={createSolution.isPending} className="w-full mt-1" />
        </div>
      </Dialog>
    </div>
  );
};
