/**
 * Instrument Management page — calibration tracking & qualification status.
 */
import { useState } from 'react';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { StatusBadge } from '@shared/components/StatusBadge';
import { toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useCreateInstrument, useInstruments } from '../hooks/useResources';
import type { Instrument } from '../models/resource.types';

const CATEGORIES = ['HPLC', 'GC', 'UV-Vis', 'Balance', 'pH Meter', 'Karl Fischer', 'Dissolution', 'Other'];

export const InstrumentsPage = () => {
  const { data: instruments = [], isLoading } = useInstruments();
  const createInstrument = useCreateInstrument();
  const { hasRole } = usePermissions();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<Partial<Instrument>>({});

  const handleCreate = () => {
    if (!form.code || !form.name) {
      toastService.warn('Code and Name are required.', 'Missing fields');
      return;
    }
    createInstrument.mutate(form, {
      onSuccess: (instrument) => {
        toastService.success(`Instrument ${instrument.code} added.`, 'Instrument Added');
        setShowModal(false);
        setForm({});
      },
    });
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{instruments.length} instruments</p>
        {hasRole('Admin') && <Button label="Add Instrument" icon="pi pi-plus" onClick={() => setShowModal(true)} />}
      </div>

      <div className="grid">
        {instruments.map((i) => (
          <div key={i.id} className="col-12 md:col-6 lg:col-4">
            <div className="bg-white border-round-lg border-1 border-200 p-3 h-full">
              <div className="flex justify-content-between align-items-start mb-2">
                <h3 className="text-sm font-semibold text-900 m-0">{i.name}</h3>
                <StatusBadge status={i.status} />
              </div>
              <p className="text-sm text-500 m-0">Code: {i.code} | {i.category}</p>
              <p className="text-xs text-400 m-0 mt-1">{i.manufacturer} {i.model_number}</p>
              <div className="mt-2 text-xs text-500">
                <p className="m-0">Location: {i.location || 'N/A'}</p>
                <p className="m-0">Cal Due: {i.calibration_due_date ? new Date(i.calibration_due_date).toLocaleDateString() : 'N/A'}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <Dialog header="Add Instrument" visible={showModal} onHide={() => setShowModal(false)} style={{ width: '440px' }} modal>
        <div className="flex flex-column gap-3">
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Code</label><InputText value={form.code || ''} onChange={(e) => setForm({ ...form, code: e.target.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Name</label><InputText value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full" /></div>
          </div>
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Category</label><Dropdown value={form.category} options={CATEGORIES} onChange={(e) => setForm({ ...form, category: e.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Location</label><InputText value={form.location || ''} onChange={(e) => setForm({ ...form, location: e.target.value })} className="w-full" /></div>
          </div>
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Manufacturer</label><InputText value={form.manufacturer || ''} onChange={(e) => setForm({ ...form, manufacturer: e.target.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Model</label><InputText value={form.model_number || ''} onChange={(e) => setForm({ ...form, model_number: e.target.value })} className="w-full" /></div>
          </div>
          <Button label="Add Instrument" onClick={handleCreate} loading={createInstrument.isPending} className="w-full mt-1" />
        </div>
      </Dialog>
    </div>
  );
};
