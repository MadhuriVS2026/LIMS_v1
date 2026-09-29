/**
 * Test Parameters master data page.
 */
import { useState } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { StatusBadge } from '@shared/components/StatusBadge';
import { toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useCreateTest, useTests } from '../hooks/useSamples';
import type { TestParameter } from '../models/sample.types';

const TEST_TYPES = ['Quantitative', 'Qualitative', 'Statistical-1', 'Statistical-2', 'Multi-Qualitative', 'Multi-Quantitative'];

export const TestsPage = () => {
  const { data: tests = [], isLoading } = useTests();
  const createTest = useCreateTest();
  const { hasRole } = usePermissions();

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<Partial<TestParameter>>({ type: 'Quantitative' });

  const handleCreate = () => {
    if (!form.code || !form.name || !form.type) {
      toastService.warn('Code, Name, and Type are required.', 'Missing fields');
      return;
    }
    createTest.mutate(form, {
      onSuccess: (test) => {
        toastService.success(`Test ${test.code} created.`, 'Test Created');
        setShowModal(false);
        setForm({ type: 'Quantitative' });
      },
    });
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{tests.length} test parameters</p>
        {hasRole('Admin') && <Button label="Add Test" icon="pi pi-plus" onClick={() => setShowModal(true)} />}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={tests} loading={isLoading} paginator rows={10} size="small">
          <Column field="code" header="Code" />
          <Column field="name" header="Name" />
          <Column field="type" header="Type" />
          <Column field="unit" header="Unit" />
          <Column field="category" header="Category" />
          <Column header="Status" body={(row) => <StatusBadge status={row.status} />} />
        </DataTable>
      </div>

      <Dialog header="Add Test Parameter" visible={showModal} onHide={() => setShowModal(false)} style={{ width: '440px' }} modal>
        <div className="flex flex-column gap-3">
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Code</label>
              <InputText value={form.code || ''} onChange={(e) => setForm({ ...form, code: e.target.value })} className="w-full" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Name</label>
              <InputText value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full" />
            </div>
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Type</label>
              <Dropdown value={form.type} options={TEST_TYPES} onChange={(e) => setForm({ ...form, type: e.value })} className="w-full" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Unit</label>
              <InputText value={form.unit || ''} onChange={(e) => setForm({ ...form, unit: e.target.value })} className="w-full" />
            </div>
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Category</label>
              <InputText value={form.category || ''} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full" placeholder="e.g., Chemical" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Technique</label>
              <InputText value={form.technique || ''} onChange={(e) => setForm({ ...form, technique: e.target.value })} className="w-full" placeholder="e.g., HPLC" />
            </div>
          </div>
          <Button label="Create Test" onClick={handleCreate} loading={createTest.isPending} className="w-full mt-1" />
        </div>
      </Dialog>
    </div>
  );
};
