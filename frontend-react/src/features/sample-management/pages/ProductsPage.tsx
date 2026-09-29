/**
 * Products/Materials master data page.
 */
import { useState } from 'react';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { InputNumber } from 'primereact/inputnumber';
import { StatusBadge } from '@shared/components/StatusBadge';
import { ESignDialog } from '@shared/components/ESignDialog';
import { toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useApproveProduct, useCreateProduct, useProducts } from '../hooks/useSamples';
import type { Product } from '../models/sample.types';

export const ProductsPage = () => {
  const { data: products = [], isLoading } = useProducts();
  const createProduct = useCreateProduct();
  const approveProduct = useApproveProduct();
  const { hasRole } = usePermissions();

  const [showModal, setShowModal] = useState(false);
  const [approveTarget, setApproveTarget] = useState<Product | null>(null);
  const [form, setForm] = useState<Partial<Product>>({});

  const handleCreate = () => {
    if (!form.code || !form.name) {
      toastService.warn('Code and Name are required.', 'Missing fields');
      return;
    }
    createProduct.mutate(form, {
      onSuccess: (product) => {
        toastService.success(`Product ${product.code} created. Pending approval.`, 'Product Created');
        setShowModal(false);
        setForm({});
      },
    });
  };

  const handleApprove = (password: string, comments?: string) => {
    if (!approveTarget) return;
    approveProduct.mutate(
      { id: approveTarget.id, password, comments },
      {
        onSuccess: (product) => {
          toastService.success(`Product ${product.code} approved and now Active.`, 'Product Approved');
          setApproveTarget(null);
        },
      }
    );
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{products.length} products</p>
        {hasRole('Admin') && <Button label="Add Product" icon="pi pi-plus" onClick={() => setShowModal(true)} />}
      </div>

      <div className="grid">
        {products.map((p) => (
          <div key={p.id} className="col-12 md:col-6 lg:col-4">
            <div className="bg-white border-round-lg border-1 border-200 p-3 h-full">
              <div className="flex justify-content-between align-items-start mb-2">
                <h3 className="text-sm font-semibold text-900 m-0">{p.name}</h3>
                <StatusBadge status={p.status} />
              </div>
              <p className="text-sm text-500 m-0 mb-2">Code: {p.code}</p>
              <p className="text-xs text-400 m-0">{p.description}</p>
              {p.status === 'Pending Approval' && hasRole('Supervisor', 'QA') && (
                <Button label="Approve" size="small" text className="mt-2 p-0" onClick={() => setApproveTarget(p)} />
              )}
            </div>
          </div>
        ))}
      </div>

      <Dialog header="Add Product" visible={showModal} onHide={() => setShowModal(false)} style={{ width: '440px' }} modal>
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
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Description</label>
            <InputTextarea value={form.description || ''} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} className="w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Retest Period (days)</label>
            <InputNumber value={form.retest_period_days} onValueChange={(e) => setForm({ ...form, retest_period_days: e.value ?? undefined })} className="w-full" />
          </div>
          <Button label="Create Product" onClick={handleCreate} loading={createProduct.isPending} className="w-full mt-1" />
        </div>
      </Dialog>

      <ESignDialog
        visible={!!approveTarget}
        onHide={() => setApproveTarget(null)}
        onConfirm={handleApprove}
        loading={approveProduct.isPending}
        title="Approve Product"
        actionLabel="Approve"
      />
    </div>
  );
};
