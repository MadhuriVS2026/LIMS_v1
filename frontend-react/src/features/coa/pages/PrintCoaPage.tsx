/**
 * Printable Certificate of Analysis.
 *
 * Renders the immutable snapshot captured at issue — header, per-test table with
 * specification/result/verdict, and the release signature chain of every
 * contributing TRF. Browser print, no server-side PDF dependency, matching the
 * ATR and Stability exports.
 *
 * Everything comes from the snapshot; nothing is re-resolved from master data.
 * That is the point: reprinting a two-year-old certificate must produce the
 * document that was issued, not one recomputed against today's specification.
 */
import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from 'primereact/button';
import { useCoa } from '../hooks/useCoa';
import type { COASignatureChain, COATestRow, Verdict } from '../models/coa.types';

const fmtDate = (value?: string | null) =>
  value ? new Date(value).toLocaleDateString() : '-';
const fmtDateTime = (value?: string | null) =>
  value ? new Date(value).toLocaleString() : '-';

const VERDICT_LABEL: Record<Verdict, string> = {
  Pass: 'Complies',
  Fail: 'Does Not Comply',
  //  Printed as an explicit statement rather than a blank, so a reader is never
  //  left to assume a verdict that was never established.
  NotEvaluated: 'Reported (no numeric limit)',
};

export const PrintCoaPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: coa, isLoading, isError } = useCoa(id ? Number(id) : undefined);

  useEffect(() => {
    document.title = coa ? `COA - ${coa.coa_number}` : 'Certificate of Analysis';
  }, [coa]);

  if (isLoading) return <p style={{ padding: '2rem' }}>Loading certificate...</p>;

  if (isError || !coa) {
    return (
      <div style={{ padding: '2rem' }}>
        <p>Certificate not found.</p>
        <Button label="Back" icon="pi pi-arrow-left" onClick={() => navigate(-1)} />
      </div>
    );
  }

  const snap = coa.snapshot;
  const tests: COATestRow[] = snap.tests ?? [];
  const signatures: COASignatureChain[] = snap.signatures ?? [];

  return (
    <div
      style={{
        maxWidth: '950px',
        margin: '0 auto',
        padding: '2rem',
        fontFamily: 'Arial, sans-serif',
        color: '#111',
      }}
    >
      <div className="no-print" style={{ marginBottom: '1rem', display: 'flex', gap: '0.5rem' }}>
        <Button label="Back" icon="pi pi-arrow-left" text onClick={() => navigate(-1)} />
        <Button label="Print / Save as PDF" icon="pi pi-print" onClick={() => window.print()} />
      </div>

      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { margin: 0; }
          .coa-table { page-break-inside: auto; }
          .coa-table tr { page-break-inside: avoid; }
        }
        table.coa-table { width: 100%; border-collapse: collapse; font-size: 11px; }
        table.coa-table th, table.coa-table td { border: 1px solid #333; padding: 4px 6px; text-align: left; vertical-align: top; }
        table.coa-table th { background: #f0f0f0; }
        .coa-fail { color: #b00020; font-weight: bold; }
      `}</style>

      <div
        style={{
          textAlign: 'center',
          borderBottom: '2px solid #000',
          paddingBottom: '0.5rem',
          marginBottom: '1rem',
        }}
      >
        <h2 style={{ margin: 0 }}>EMCURE</h2>
        <p style={{ margin: 0 }}>R&amp;D</p>
        <p style={{ margin: 0, fontWeight: 'bold' }}>CERTIFICATE OF ANALYSIS</p>
        <p style={{ margin: 0, fontSize: '12px' }}>
          COA No.: {coa.coa_number} — Issued: {fmtDate(snap.generated_at)}
        </p>
      </div>

      <table className="coa-table" style={{ marginBottom: '1rem' }}>
        <tbody>
          <tr>
            <td><strong>Product</strong></td>
            <td>{snap.product?.name ?? '-'}</td>
            <td><strong>Product Code</strong></td>
            <td>{snap.product?.code ?? '-'}</td>
          </tr>
          <tr>
            <td><strong>Batch Number</strong></td>
            <td>{snap.batch?.batch_number ?? coa.batch_number}</td>
            <td><strong>Label Claim</strong></td>
            <td>{snap.batch?.label_claim || '-'}</td>
          </tr>
          <tr>
            <td><strong>Stage of Sample</strong></td>
            <td>{snap.batch?.stage_of_sample || '-'}</td>
            <td><strong>Pack Details</strong></td>
            <td>{snap.batch?.pack_details || '-'}</td>
          </tr>
          <tr>
            <td><strong>Manufactured By</strong></td>
            <td>{snap.batch?.manufactured_by || '-'}</td>
            <td><strong>Mfg. Date</strong></td>
            <td>{fmtDate(snap.batch?.mfg_date)}</td>
          </tr>
          <tr>
            <td><strong>Expiry / Retest Date</strong></td>
            <td>{fmtDate(snap.batch?.expiry_or_retest_date)}</td>
            <td><strong>Storage Condition</strong></td>
            <td>
              {snap.batch?.storage_condition || snap.product?.storage_condition || '-'}
            </td>
          </tr>
          <tr>
            <td><strong>Specification</strong></td>
            <td>
              {snap.specification
                ? `${snap.specification.document_no ?? '-'} (v${snap.specification.version})`
                : 'Not specified'}
            </td>
            <td><strong>TRF / AR References</strong></td>
            <td>
              {(snap.references?.trf_numbers ?? []).join(', ') || '-'}
              {snap.references?.ar_numbers?.length
                ? ` / ${snap.references.ar_numbers.join(', ')}`
                : ''}
            </td>
          </tr>
        </tbody>
      </table>

      <h4 style={{ marginBottom: '0.25rem' }}>Test Results</h4>
      <table className="coa-table" style={{ marginBottom: '1rem' }}>
        <thead>
          <tr>
            <th style={{ width: '2.5rem' }}>#</th>
            <th>Test</th>
            <th>Specification</th>
            <th>Result</th>
            <th style={{ width: '10rem' }}>Conclusion</th>
          </tr>
        </thead>
        <tbody>
          {tests.length === 0 && (
            <tr>
              <td colSpan={5}>No results reported.</td>
            </tr>
          )}
          {tests.map((row, index) => (
            <tr key={`${row.test_id}-${index}`}>
              <td>{index + 1}</td>
              <td>
                {row.test_name ?? row.test_code ?? `Test #${row.test_id}`}
                {row.template_code && (
                  <div style={{ fontSize: '9px', color: '#555' }}>
                    {row.template_code} v{row.template_version}
                  </div>
                )}
              </td>
              <td>
                {row.specification_text || '-'}
                {row.limit_unit && (
                  <span style={{ color: '#555' }}> ({row.limit_unit})</span>
                )}
              </td>
              <td>{row.result_text || '-'}</td>
              <td className={row.verdict === 'Fail' ? 'coa-fail' : undefined}>
                {VERDICT_LABEL[row.verdict] ?? row.verdict}
                {/* States *why* a row could not be judged, so a NotEvaluated is
                    never mistaken for an omission or an implied pass. */}
                {row.verdict === 'NotEvaluated' && row.not_evaluated_reason && (
                  <div style={{ fontSize: '9px', color: '#555' }}>
                    {row.not_evaluated_reason}
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <table className="coa-table" style={{ marginBottom: '1rem' }}>
        <tbody>
          <tr>
            <td style={{ width: '12rem' }}><strong>Overall Conclusion</strong></td>
            <td className={snap.overall_verdict === 'Fail' ? 'coa-fail' : undefined}>
              {VERDICT_LABEL[snap.overall_verdict] ?? snap.overall_verdict}
            </td>
          </tr>
          {snap.remarks && (
            <tr>
              <td><strong>Remarks</strong></td>
              <td>{snap.remarks}</td>
            </tr>
          )}
        </tbody>
      </table>

      <h4 style={{ marginBottom: '0.25rem' }}>Release Signature Chain</h4>
      {signatures.map((chain) => (
        <table className="coa-table" style={{ marginBottom: '0.75rem' }} key={chain.trf_number}>
          <thead>
            <tr>
              <th colSpan={5} style={{ fontWeight: 'normal' }}>
                {chain.trf_number}
                {chain.ar_number ? ` — AR ${chain.ar_number}` : ''}
              </th>
            </tr>
            <tr>
              <th>Initiated By</th>
              <th>Approved By (FDGL)</th>
              <th>Accepted By (ADGL)</th>
              <th>Analysed By</th>
              <th>Released By (ADGL)</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ height: '40px' }}>
              <td>{chain.initiated_by || '-'}</td>
              <td>{chain.fdgl_approved_by || '-'}</td>
              <td>{chain.adgl_accepted_by || '-'}</td>
              <td>{chain.analyst_accepted_by || '-'}</td>
              <td>{chain.released_by || '-'}</td>
            </tr>
            <tr>
              <td>{fmtDateTime(chain.initiated_at)}</td>
              <td>{fmtDateTime(chain.fdgl_approved_at)}</td>
              <td>{fmtDateTime(chain.adgl_accepted_at)}</td>
              <td>{fmtDateTime(chain.analyst_accepted_at)}</td>
              <td>{fmtDateTime(chain.released_at)}</td>
            </tr>
          </tbody>
        </table>
      ))}

      <table className="coa-table" style={{ marginTop: '1rem' }}>
        <thead>
          <tr>
            <th>Certificate Issued By</th>
            <th>Role</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          <tr style={{ height: '40px' }}>
            <td>{snap.issued_by?.full_name ?? coa.released_by}</td>
            <td>{snap.issued_by?.role ?? '-'}</td>
            <td>{fmtDateTime(coa.released_at ?? snap.generated_at)}</td>
          </tr>
        </tbody>
      </table>

      <p style={{ fontSize: '10px', color: '#555', marginTop: '1rem' }}>
        This certificate was generated electronically from released Test Request Forms and is
        e-signed per 21 CFR Part 11. Its contents were captured at issue and are not affected by
        later changes to product, specification, or template data.
      </p>
    </div>
  );
};
