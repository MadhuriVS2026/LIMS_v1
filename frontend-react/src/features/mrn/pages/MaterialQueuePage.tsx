/**
 * Material Queue page — GRN-completed material lots pulled from SAP CPI,
 * available for requisition against a Material Requisition (MRN).
 *
 * Unified flow: select one or more lots from the queue, set the requested
 * quantity + project code for each right here, then "Raise MRN" creates the
 * MRN header and all its line items in one action — no separate "create an
 * empty Draft, then go add items" step.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { InputNumber } from 'primereact/inputnumber';
import { InputText } from 'primereact/inputtext';
import { StatusBadge } from '@shared/components/StatusBadge';
import { toastService, getErrorMessage } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useCreateMRN, useAddLineItem, useMaterialQueue, usePullMaterialQueue } from '../hooks/useMrn';
import type { MRNMaterialLot } from '../models/mrn.types';

interface CartItem {
  lot: MRNMaterialLot;
  quantity: number | null;
  projectCode: string;
}

export const MaterialQueuePage = () => {
  const navigate = useNavigate();
  const { hasRole } = usePermissions();
  const canPull = hasRole('Admin', 'Analyst', 'Supervisor');
  const canRaiseMRN = hasRole('Admin', 'Analyst');
  const { data: lots = [], isLoading } = useMaterialQueue();
  const pullQueue = usePullMaterialQueue();
  const createMRN = useCreateMRN();
  const addLineItem = useAddLineItem();

  const [selectedLots, setSelectedLots] = useState<MRNMaterialLot[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [raising, setRaising] = useState(false);

  const handlePull = () => {
    pullQueue.mutate(undefined, {
      onSuccess: (result) => toastService.success(`Pulled ${result.pulled} lot(s) from SAP.`, 'Material Queue Updated'),
      onError: (e) => toastService.error(getErrorMessage(e), 'Pull from SAP Failed'),
    });
  };

  const handleAddSelectedToCart = () => {
    const existingIds = new Set(cart.map((c) => c.lot.id));
    const toAdd = selectedLots
      .filter((lot) => !existingIds.has(lot.id))
      .map((lot) => ({ lot, quantity: lot.available_quantity, projectCode: '' }));
    setCart([...cart, ...toAdd]);
    setSelectedLots([]);
  };

  const updateCartItem = (lotId: number, patch: Partial<CartItem>) => {
    setCart(cart.map((c) => (c.lot.id === lotId ? { ...c, ...patch } : c)));
  };

  const removeCartItem = (lotId: number) => {
    setCart(cart.filter((c) => c.lot.id !== lotId));
  };

  const handleRaiseMRN = async () => {
    const invalid = cart.find(
      (c) => !c.quantity || c.quantity <= 0 || c.quantity > c.lot.available_quantity || !c.projectCode.trim()
    );
    if (invalid) {
      toastService.warn(
        `Check ${invalid.lot.material_code}: quantity must be > 0 and within available stock, and project code is required.`,
        'Cannot Raise MRN'
      );
      return;
    }

    setRaising(true);
    try {
      const mrn = await createMRN.mutateAsync();
      for (const item of cart) {
        await addLineItem.mutateAsync({
          mrnId: mrn.id,
          payload: {
            lot_id: item.lot.id,
            requested_quantity: item.quantity as number,
            project_code: item.projectCode.trim(),
          },
        });
      }
      toastService.success(`${mrn.mrn_number} raised with ${cart.length} line item(s).`, 'MRN Raised');
      setCart([]);
      navigate(`/mrn/${mrn.id}`);
    } catch (e) {
      toastService.error(getErrorMessage(e), 'Could Not Raise MRN');
    } finally {
      setRaising(false);
    }
  };

  const cartLotIds = new Set(cart.map((c) => c.lot.id));

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{lots.length} material lot(s) available</p>
        <div className="flex gap-2">
          {canRaiseMRN && selectedLots.length > 0 && (
            <Button
              label={`Add ${selectedLots.length} to MRN`}
              icon="pi pi-cart-plus"
              severity="secondary"
              outlined
              onClick={handleAddSelectedToCart}
            />
          )}
          {canPull && (
            <Button
              label="Pull from SAP"
              icon="pi pi-cloud-download"
              onClick={handlePull}
              loading={pullQueue.isPending}
            />
          )}
        </div>
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden mb-4">
        <DataTable
          value={lots}
          loading={isLoading}
          paginator
          rows={10}
          size="small"
          dataKey="id"
          selectionMode={canRaiseMRN ? 'checkbox' : null}
          selection={selectedLots}
          onSelectionChange={(e: { value: MRNMaterialLot[] }) => setSelectedLots(e.value)}
          emptyMessage="No GRN-complete material lots available. Pull from SAP to refresh."
        >
          {canRaiseMRN && <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} />}
          <Column header="GRN Reference" body={(row: MRNMaterialLot) => (
            <span className="font-mono text-sm">{row.grn_document_no}/{row.grn_item_no}</span>
          )} />
          <Column field="material_code" header="Material Code" />
          <Column field="material_description" header="Description" />
          <Column field="batch_number" header="Batch" />
          <Column field="plant" header="Plant" />
          <Column header="Available Qty" body={(row: MRNMaterialLot) => `${row.available_quantity} ${row.unit}`} />
          <Column header="Status" body={(row: MRNMaterialLot) => <StatusBadge status={row.status} />} />
          <Column header="GRN Date" body={(row: MRNMaterialLot) => (row.grn_date ? new Date(row.grn_date).toLocaleDateString() : '-')} />
          {canRaiseMRN && (
            <Column
              header=""
              body={(row: MRNMaterialLot) =>
                cartLotIds.has(row.id) ? (
                  <span className="text-sm text-500">In MRN cart</span>
                ) : (
                  <Button
                    label="Add"
                    text
                    size="small"
                    onClick={() => setCart([...cart, { lot: row, quantity: row.available_quantity, projectCode: '' }])}
                  />
                )
              }
            />
          )}
        </DataTable>
      </div>

      {canRaiseMRN && cart.length > 0 && (
        <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
          <h3 className="text-base font-semibold text-900 m-0 p-3 pb-0">New MRN — Line Items</h3>
          <p className="text-sm text-500 m-0 px-3 pb-2">
            Set the requested quantity and project code for each material, then raise the MRN.
          </p>
          <DataTable value={cart} size="small" dataKey="lot.id">
            <Column header="Material" body={(row: CartItem) => `${row.lot.material_code} — ${row.lot.batch_number || 'no batch'}`} />
            <Column header="Available" body={(row: CartItem) => `${row.lot.available_quantity} ${row.lot.unit}`} />
            <Column
              header="Requested Quantity"
              body={(row: CartItem) => (
                <InputNumber
                  value={row.quantity}
                  onValueChange={(e) => updateCartItem(row.lot.id, { quantity: e.value ?? null })}
                  max={row.lot.available_quantity}
                  min={0}
                  size={6}
                />
              )}
            />
            <Column
              header="Project Code"
              body={(row: CartItem) => (
                <InputText
                  value={row.projectCode}
                  onChange={(e) => updateCartItem(row.lot.id, { projectCode: e.target.value })}
                  placeholder="e.g. PROJ-001"
                />
              )}
            />
            <Column
              header=""
              body={(row: CartItem) => (
                <Button icon="pi pi-trash" text size="small" severity="danger" onClick={() => removeCartItem(row.lot.id)} />
              )}
            />
          </DataTable>
          <div className="p-3 flex justify-content-end">
            <Button
              label={`Raise MRN with ${cart.length} Line Item(s)`}
              icon="pi pi-send"
              severity="success"
              loading={raising}
              onClick={handleRaiseMRN}
            />
          </div>
        </div>
      )}
    </div>
  );
};
