/**
 * Specifications master data page — versioned test limits per Product.
 */
import { useState } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { Dropdown } from 'primereact/dropdown';
import { InputNumber } from 'primereact/inputnumber';
import { InputText } from 'primereact/inputtext';
import { Checkbox } from 'primereact/checkbox';
import { StatusBadge } from '@shared/components/StatusBadge';
import { ESignDialog } from '@shared/components/ESignDialog';
import { toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import {
  useApproveSpecification,
  useCreateSpecification,
  useProducts,
  useSpecifications,
  useTests,
} from '../hooks/useSamples';
import type { Specification, SpecTestItem } from '../models/sample.types';

const SPEC_TYPES = ['Regulatory', 'Release', 'Tentative', 'Working Standard', 'Shelf Life'];

export const SpecificationsPage = () => {
  const { data: specs = [], isLoading } = useSpecifications();
  const { data: products = [] } = useProducts();
  const { data: tests = [] } = useTests();
  const approveSpec = useApproveSpecification();
  const createSpec = useCreateSpecification();
  const { hasRole } = usePermissions();

  const [approveTarget, setApproveTarget] = useState<Specification | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [productId, setProductId] = useState<number | null>(null);
  const [specType, setSpecType] = useState(SPEC_TYPES[1]);
  const [documentNo, setDocumentNo] = useState('');
  const [selectedTests, setSelectedTests] = useState<Record<number, SpecTestItem>>({});

  const activeProducts = products.filter((p) => p.status === 'Active');
  const activeTests = tests.filter((t) => t.status === 'Active');

  const toggleTest = (testId: number, checked: boolean) => {
    setSelectedTests((prev) => {
      const next = { ...prev };
      if (checked) {
        next[testId] = { test_id: testId, display_in_coa: true };
      } else {
        delete next[testId];
      }
      return next;
    });
  };

  const updateTestLimit = (testId: number, field: keyof SpecTestItem, value: string | number | null) => {
    setSelectedTests((prev) => ({
      ...prev,
      [testId]: { ...prev[testId], [field]: value },
    }));
  };

  const resetForm = () => {
    setProductId(null);
    setSpecType(SPEC_TYPES[1]);
    setDocumentNo('');
    setSelectedTests({});
  };

  const handleCreate = () => {
    const testList = Object.values(selectedTests);
    if (!productId) {
      toastService.warn('Please select a product.', 'Missing product');
      return;
    }
    if (testList.length === 0) {
      toastService.warn('Please select at least one test and enter its limits.', 'No tests selected');
      return;
    }
    createSpec.mutate(
      { product_id: productId, spec_type: specType, document_no: documentNo || undefined, tests: testList },
      {
        onSuccess: (spec) => {
          toastService.success(`Specification v${spec.version} created with ${spec.tests.length} tests. Pending approval.`, 'Specification Created');
          setShowModal(false);
          resetForm();
        },
      }
    );
  };

  const handleApprove = (password: string, comments?: string) => {
    if (!approveTarget) return;
    approveSpec.mutate(
      { id: approveTarget.id, password, comments },
      {
        onSuccess: (spec) => {
          toastService.success(`Specification v${spec.version} approved and now Active.`, 'Specification Approved');
          setApproveTarget(null);
        },
      }
    );
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{specs.length} specifications</p>
        {hasRole('Admin') && <Button label="Create Specification" icon="pi pi-plus" onClick={() => setShowModal(true)} />}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={specs} loading={isLoading} paginator rows={10} size="small">
          <Column header="Product" body={(row) => row.product?.name} />
          <Column header="Version" body={(row) => `v${row.version}`} />
          <Column header="Tests" body={(row) => `${row.tests.length} tests`} />
          <Column header="Status" body={(row) => <StatusBadge status={row.status} />} />
          <Column
            header="Actions"
            body={(row) =>
              row.status === 'Pending Approval' && hasRole('Supervisor', 'QA') ? (
                <Button label="Approve" size="small" text onClick={() => setApproveTarget(row)} />
              ) : null
            }
          />
        </DataTable>
      </div>

      <Dialog header="Create Specification" visible={showModal} onHide={() => { setShowModal(false); resetForm(); }} style={{ width: '600px' }} modal>
        <div className="flex flex-column gap-3">
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Product</label>
              <Dropdown
                value={productId}
                options={activeProducts.map((p) => ({ label: `${p.name} (${p.code})`, value: p.id }))}
                onChange={(e) => setProductId(e.value)}
                placeholder="Select product..."
                className="w-full"
              />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Specification Type</label>
              <Dropdown value={specType} options={SPEC_TYPES} onChange={(e) => setSpecType(e.value)} className="w-full" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Document No. (Optional)</label>
            <InputText value={documentNo} onChange={(e) => setDocumentNo(e.target.value)} className="w-full" placeholder="e.g., STP-001" />
          </div>

          <div>
            <label className="block text-sm font-medium text-700 mb-2">Select Tests &amp; Limits</label>
            {activeTests.length === 0 && <p className="text-sm text-500">No active tests available. Create tests first.</p>}
            <div className="flex flex-column gap-2" style={{ maxHeight: '280px', overflowY: 'auto' }}>
              {activeTests.map((test) => {
                const isSelected = !!selectedTests[test.id];
                const isQualitative = test.type !== 'Quantitative';
                return (
                  <div key={test.id} className="border-1 border-200 border-round p-2">
                    <div className="flex align-items-center gap-2 mb-2">
                      <Checkbox checked={isSelected} onChange={(e) => toggleTest(test.id, e.checked ?? false)} />
                      <span className="text-sm font-medium">{test.name}</span>
                      <span className="text-xs text-500">({test.code} — {test.type})</span>
                    </div>
                    {isSelected && (
                      <div className="grid pl-4">
                        {isQualitative ? (
                          <div className="col-12">
                            <InputText
                              placeholder="Expected result (e.g., Complies)"
                              value={selectedTests[test.id]?.expected_result ?? ''}
                              onChange={(e) => updateTestLimit(test.id, 'expected_result', e.target.value)}
                              className="w-full"
                            />
                          </div>
                        ) : (
                          <>
                            <div className="col-6">
                              <InputNumber
                                placeholder="Min limit"
                                value={selectedTests[test.id]?.min_limit ?? null}
                                onValueChange={(e) => updateTestLimit(test.id, 'min_limit', e.value ?? null)}
                                className="w-full"
                                maxFractionDigits={4}
                              />
                            </div>
                            <div className="col-6">
                              <InputNumber
                                placeholder="Max limit"
                                value={selectedTests[test.id]?.max_limit ?? null}
                                onValueChange={(e) => updateTestLimit(test.id, 'max_limit', e.value ?? null)}
                                className="w-full"
                                maxFractionDigits={4}
                              />
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <Button label="Create Specification" onClick={handleCreate} loading={createSpec.isPending} className="w-full mt-1" />
        </div>
      </Dialog>

      <ESignDialog
        visible={!!approveTarget}
        onHide={() => setApproveTarget(null)}
        onConfirm={handleApprove}
        loading={approveSpec.isPending}
        title="Approve Specification"
        actionLabel="Approve"
      />
    </div>
  );
};
