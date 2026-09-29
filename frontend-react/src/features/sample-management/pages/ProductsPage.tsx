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
import {
  useApproveProduct,
  useCreateProduct,
  useDeleteProduct,
  useProducts,
  useUpdateProduct,
} from '../hooks/useSamples';
import type { Product } from '../models/sample.types';

export const ProductsPage = () => {
  const { data: products = [], isLoading } = useProducts();
  const createProduct = useCreateProduct();
  const approveProduct = useApproveProduct();
  const updateProduct = useUpdateProduct();
  const deleteProduct = useDeleteProduct();
  const { hasRole } = usePermissions();

  const [showModal, setShowModal] = useState(false);
  const [approveTarget, setApproveTarget] = useState<Product | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Product | null>(null);
  const [editTarget, setEditTarget] = useState<Product | null>(null);
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

  const openEdit = (product: Product) => {
    setEditTarget(product);
    setForm({
      name: product.name,
      description: product.description ?? '',
      material_type: product.material_type ?? '',
      retest_period_days: product.retest_period_days ?? undefined,
      storage_condition: product.storage_condition ?? '',
    });
  };

  const handleUpdate = () => {
    if (!editTarget) return;
    if (!form.name) {
      toastService.warn('Name is required.', 'Missing fields');
      return;
    }
    updateProduct.mutate(
      {
        id: editTarget.id,
        payload: {
          name: form.name,
          description: form.description,
          material_type: form.material_type,
          retest_period_days: form.retest_period_days,
          storage_condition: form.storage_condition,
        },
      },
      {
        onSuccess: (product) => {
          const note =
            product.status === 'Pending Approval'
              ? `Product ${product.code} updated. Returned to Pending Approval — re-approval required.`
              : `Product ${product.code} updated.`;
          toastService.success(note, 'Product Updated');
          setEditTarget(null);
          setForm({});
        },
      }
    );
  };

  const handleDelete = (password: string, comments?: string) => {
    if (!deleteTarget) return;
    deleteProduct.mutate(
      { id: deleteTarget.id, password, comments },
      {
        onSuccess: (product) => {
          toastService.success(`Product ${product.code} deactivated. GL/TL/Supervisor notified for review.`, 'Product Deactivated');
          setDeleteTarget(null);
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
              <div className="flex gap-2 mt-2 flex-wrap">
                {p.status === 'Pending Approval' && hasRole('Supervisor', 'QA') && (
                  <Button label="Approve" size="small" text className="p-0" onClick={() => setApproveTarget(p)} />
                )}
                {p.status !== 'Inactive' && hasRole('Admin') && (
                  <Button label="Edit" size="small" text className="p-0" onClick={() => openEdit(p)} />
                )}
                {p.status !== 'Inactive' && hasRole('Admin', 'Supervisor') && (
                  <Button label="Delete" size="small" text severity="danger" className="p-0" onClick={() => setDeleteTarget(p)} />
                )}
              </div>
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

      <Dialog header={`Edit Product${editTarget ? ` — ${editTarget.code}` : ''}`} visible={!!editTarget} onHide={() => { setEditTarget(null); setForm({}); }} style={{ width: '440px' }} modal>
        <div className="flex flex-column gap-3">
          {editTarget?.status === 'Active' && (
            <div className="text-sm bg-yellow-50 border-round p-2 border-1 border-yellow-200">
              <i className="pi pi-exclamation-triangle mr-2 text-yellow-700" />
              This product is Active. Saving changes returns it to Pending Approval and requires re-approval.
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Name</label>
            <InputText value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Description</label>
            <InputTextarea value={form.description || ''} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} className="w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Material Type</label>
            <InputText value={form.material_type || ''} onChange={(e) => setForm({ ...form, material_type: e.target.value })} className="w-full" placeholder="RM, PM, FG, IP" />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Retest Period (days)</label>
            <InputNumber value={form.retest_period_days} onValueChange={(e) => setForm({ ...form, retest_period_days: e.value ?? undefined })} onChange={(e) => setForm({ ...form, retest_period_days: e.value ?? undefined })} className="w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Storage Condition</label>
            <InputText value={form.storage_condition || ''} onChange={(e) => setForm({ ...form, storage_condition: e.target.value })} className="w-full" />
          </div>
          <Button label="Save Changes" onClick={handleUpdate} loading={updateProduct.isPending} className="w-full mt-1" />
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

      <ESignDialog
        visible={!!deleteTarget}
        onHide={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        loading={deleteProduct.isPending}
        title={`Deactivate Product${deleteTarget ? ` — ${deleteTarget.code}` : ''}`}
        actionLabel="Deactivate"
      />
    </div>
  );
};
