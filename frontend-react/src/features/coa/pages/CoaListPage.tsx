/**
 * Certificate of Analysis list, and the generation flow.
 *
 * Generation is two-step by design: **Compile** first, which shows exactly what
 * the certificate would say including any failing or unevaluated test, and only
 * then **Sign & Issue**. A certificate is immutable once issued, so a signature
 * committed to an unseen document would be unfixable.
 */
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from 'primereact/button';
import { Column } from 'primereact/column';
import { DataTable } from 'primereact/datatable';
import { Dialog } from 'primereact/dialog';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Message } from 'primereact/message';
import { Tag } from 'primereact/tag';
import { ESignDialog } from '@shared/components/ESignDialog';
import { getErrorMessage, toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useProducts } from '@features/sample-management/hooks/useSamples';
import { useCoaList, useGenerateCoa, usePreviewCoa } from '../hooks/useCoa';
import { VerdictTag } from '../components/VerdictTag';
import type { COASnapshot, COASummary } from '../models/coa.types';

export const CoaListPage = () => {
  const navigate = useNavigate();
  const { hasRole } = usePermissions();
  const canIssue = hasRole('Admin', 'QA');

  const { data: coas = [], isLoading } = useCoaList();
  const { data: products = [] } = useProducts();
  const preview = usePreviewCoa();
  const generate = useGenerateCoa();

  const [showGenerate, setShowGenerate] = useState(false);
  const [productId, setProductId] = useState<number | null>(null);
  const [batchNumber, setBatchNumber] = useState('');
  const [remarks, setRemarks] = useState('');
  const [compiled, setCompiled] = useState<COASnapshot | null>(null);
  const [showEsign, setShowEsign] = useState(false);

  const activeProducts = useMemo(
    () => products.filter((p) => p.status === 'Active'),
    [products],
  );

  const closeGenerate = () => {
    setShowGenerate(false);
    setProductId(null);
    setBatchNumber('');
    setRemarks('');
    setCompiled(null);
  };

  const handleCompile = () => {
    if (productId == null || !batchNumber.trim()) {
      toastService.warn('Product and Batch Number are required.', 'Missing Fields');
      return;
    }
    setCompiled(null);
    preview.mutate(
      { product_id: productId, batch_number: batchNumber.trim() },
      {
        onSuccess: (snapshot) => setCompiled(snapshot),
        onError: (e) => toastService.error(getErrorMessage(e), 'Nothing To Certify'),
      },
    );
  };

  const handleIssue = (password: string) => {
    if (productId == null) return;
    generate.mutate(
      {
        product_id: productId,
        batch_number: batchNumber.trim(),
        remarks: remarks.trim() || null,
        password,
      },
      {
        onSuccess: (coa) => {
          setShowEsign(false);
          toastService.success(`${coa.coa_number} issued.`, 'Certificate Issued');
          closeGenerate();
          navigate(`/coa/${coa.id}/print`);
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Issue Certificate'),
      },
    );
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{coas.length} certificate(s)</p>
        {canIssue && (
          <Button
            label="Generate COA"
            icon="pi pi-file-check"
            onClick={() => setShowGenerate(true)}
          />
        )}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable
          value={coas}
          loading={isLoading}
          paginator
          rows={10}
          size="small"
          emptyMessage="No certificates issued yet."
        >
          <Column
            field="coa_number"
            header="COA Number"
            body={(row: COASummary) => (
              <span className="font-mono text-blue-600">{row.coa_number}</span>
            )}
          />
          <Column
            header="Product"
            body={(row: COASummary) =>
              row.product_name ? `${row.product_name} (${row.product_code})` : '-'
            }
          />
          <Column field="batch_number" header="Batch" />
          <Column
            header="Result"
            body={(row: COASummary) => <VerdictTag verdict={row.overall_verdict} />}
          />
          <Column header="Tests" body={(row: COASummary) => row.test_count} />
          <Column field="released_by" header="Issued By" />
          <Column
            header="Issued"
            body={(row: COASummary) =>
              row.released_at ? new Date(row.released_at).toLocaleString() : '-'
            }
          />
          <Column
            header="Actions"
            body={(row: COASummary) => (
              <Button
                label="Print"
                icon="pi pi-print"
                size="small"
                text
                onClick={() => navigate(`/coa/${row.id}/print`)}
              />
            )}
          />
        </DataTable>
      </div>

      <Dialog
        header="Generate Certificate of Analysis"
        visible={showGenerate}
        onHide={closeGenerate}
        style={{ width: '820px' }}
        modal
      >
        <div className="flex flex-column gap-3">
          <div className="grid">
            <div className="col-7">
              <label className="block text-sm font-medium text-700 mb-1">Product</label>
              <Dropdown
                value={productId}
                options={activeProducts.map((p) => ({
                  label: `${p.name} (${p.code})`,
                  value: p.id,
                }))}
                onChange={(e) => {
                  setProductId(e.value);
                  setCompiled(null);
                }}
                placeholder="Select product..."
                className="w-full"
                filter
              />
            </div>
            <div className="col-5">
              <label className="block text-sm font-medium text-700 mb-1">Batch Number</label>
              <InputText
                value={batchNumber}
                onChange={(e) => {
                  setBatchNumber(e.target.value);
                  setCompiled(null);
                }}
                className="w-full"
              />
            </div>
          </div>

          <div className="flex align-items-center gap-2">
            <Button
              label="Compile"
              icon="pi pi-search"
              outlined
              onClick={handleCompile}
              loading={preview.isPending}
            />
            <small className="text-500">
              Compiles the released results for this batch so you can review them before signing.
            </small>
          </div>

          {compiled && (
            <>
              {compiled.overall_verdict === 'Fail' && (
                <Message
                  severity="error"
                  className="w-full"
                  text="One or more results are outside specification. The certificate will record the failure."
                />
              )}
              {compiled.overall_verdict === 'NotEvaluated' && (
                <Message
                  severity="warn"
                  className="w-full"
                  text="No result could be compared against a numeric specification limit, so no pass can be certified. Check that an Active specification exists for this product."
                />
              )}
              {compiled.specification == null && (
                <Message
                  severity="warn"
                  className="w-full"
                  text="This product has no Active specification, so every result will be reported without a verdict."
                />
              )}

              <div className="border-1 border-200 border-round p-3">
                <div className="flex justify-content-between align-items-center mb-2">
                  <span className="font-medium">
                    {compiled.product.name} · batch {compiled.batch.batch_number}
                  </span>
                  <div className="flex align-items-center gap-2">
                    <Tag value={`Pass ${compiled.verdict_counts.Pass}`} severity="success" />
                    <Tag value={`Fail ${compiled.verdict_counts.Fail}`} severity="danger" />
                    <Tag
                      value={`Not evaluated ${compiled.verdict_counts.NotEvaluated}`}
                      severity="secondary"
                    />
                  </div>
                </div>
                <p className="text-xs text-500 m-0 mb-2">
                  From {compiled.references.trf_numbers.join(', ') || '-'}
                </p>
                <DataTable value={compiled.tests} size="small" className="text-sm">
                  <Column
                    header="Test"
                    body={(row) => row.test_name ?? row.test_code ?? `#${row.test_id}`}
                  />
                  <Column field="specification_text" header="Specification" />
                  <Column field="result_text" header="Result" />
                  <Column
                    header="Verdict"
                    body={(row) => (
                      <div className="flex flex-column gap-1">
                        <VerdictTag verdict={row.verdict} />
                        {/* Surfaced during the compile step so QA sees an
                            unjudgeable row before signing, not after. */}
                        {row.verdict === 'NotEvaluated' && row.not_evaluated_reason && (
                          <span className="text-xs text-500">
                            {row.not_evaluated_reason}
                          </span>
                        )}
                      </div>
                    )}
                  />
                  <Column
                    header="Source"
                    body={(row) => (
                      <span className="text-xs text-500">
                        {row.source === 'Worksheet'
                          ? `${row.template_code} v${row.template_version}`
                          : 'Free text'}
                      </span>
                    )}
                  />
                </DataTable>
              </div>

              <div>
                <label className="block text-sm font-medium text-700 mb-1">Remarks</label>
                <InputTextarea
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  rows={2}
                  className="w-full"
                  placeholder="Optional note printed on the certificate"
                />
              </div>

              <Message
                severity="info"
                className="w-full"
                text="A certificate cannot be edited once issued. A correction is a new certificate that supersedes this one."
              />

              <Button
                label="Sign & Issue Certificate"
                icon="pi pi-check"
                onClick={() => setShowEsign(true)}
                disabled={compiled.tests.length === 0}
              />
            </>
          )}
        </div>
      </Dialog>

      <ESignDialog
        visible={showEsign}
        title="Issue Certificate of Analysis"
        actionLabel="Sign & Issue"
        showComments={false}
        loading={generate.isPending}
        onHide={() => setShowEsign(false)}
        onConfirm={handleIssue}
      />
    </div>
  );
};
