/**
 * Printable Analytical Test Report (ATR) — renders the immutable snapshot
 * captured at release time (header block, test-details table, remarks, and
 * the full 5-signature chain: Initiated/Approved/Accepted/Analysed/
 * Released By with role and date). Follows the same browser-print pattern
 * as the Stability Protocol/Report exports.
 */
import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from 'primereact/button';
import { useATR } from '../hooks/useTRF';

const fmtDateTime = (value?: string | null) => (value ? new Date(value).toLocaleString() : '-');

export const PrintATRPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const trfId = Number(id);
  const { data: atr, isLoading, isError } = useATR(trfId);

  useEffect(() => {
    document.title = atr ? `ATR - ${atr.trf_number}` : 'Analytical Test Report';
  }, [atr]);

  if (isLoading) {
    return <p style={{ padding: '2rem' }}>Loading ATR...</p>;
  }

  if (isError || !atr) {
    return (
      <div style={{ padding: '2rem' }}>
        <p>ATR is only available once the TRF has been Released.</p>
        <Button label="Back" icon="pi pi-arrow-left" onClick={() => navigate(-1)} />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '950px', margin: '0 auto', padding: '2rem', fontFamily: 'Arial, sans-serif', color: '#111' }}>
      <div className="no-print" style={{ marginBottom: '1rem', display: 'flex', gap: '0.5rem' }}>
        <Button label="Back" icon="pi pi-arrow-left" text onClick={() => navigate(-1)} />
        <Button label="Print / Save as PDF" icon="pi pi-print" onClick={() => window.print()} />
      </div>

      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { margin: 0; }
        }
        table.atr-table { width: 100%; border-collapse: collapse; font-size: 11px; }
        table.atr-table th, table.atr-table td { border: 1px solid #333; padding: 4px 6px; text-align: left; }
        table.atr-table th { background: #f0f0f0; }
      `}</style>

      <div style={{ textAlign: 'center', borderBottom: '2px solid #000', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0 }}>EMCURE</h2>
        <p style={{ margin: 0 }}>R&amp;D</p>
        <p style={{ margin: 0, fontWeight: 'bold' }}>ANALYTICAL TEST REPORT (ATR)</p>
        <p style={{ margin: 0, fontSize: '12px' }}>
          TRF No.: {atr.trf_number} {atr.ar_number ? `— AR No.: ${atr.ar_number}` : ''}
        </p>
      </div>

      <table className="atr-table" style={{ marginBottom: '1rem' }}>
        <tbody>
          <tr><td><strong>Batch Number</strong></td><td>{atr.batch_number}</td><td><strong>Label Claim</strong></td><td>{atr.label_claim || '-'}</td></tr>
          <tr><td><strong>Stage of Sample</strong></td><td>{atr.stage_of_sample || '-'}</td><td><strong>Storage Condition</strong></td><td>{atr.storage_condition || '-'}</td></tr>
          <tr><td><strong>Storage Period</strong></td><td>{atr.storage_period || '-'}</td><td><strong>Pack Details</strong></td><td>{atr.pack_details || '-'}</td></tr>
          <tr><td><strong>Manufactured By</strong></td><td>{atr.manufactured_by || '-'}</td><td><strong>Mfg. Date</strong></td><td>{fmtDateTime(atr.mfg_date)}</td></tr>
          <tr><td><strong>Expiry / Retest Date</strong></td><td>{fmtDateTime(atr.expiry_or_retest_date)}</td><td><strong>Remark</strong></td><td>{atr.remark || '-'}</td></tr>
        </tbody>
      </table>

      <h4 style={{ marginBottom: '0.25rem' }}>Test Details</h4>
      <table className="atr-table" style={{ marginBottom: '1rem' }}>
        <thead>
          <tr>
            <th>#</th>
            <th>Test</th>
            <th>Specification</th>
            <th>Raw Data Reference</th>
            <th>Result</th>
            <th>Remark</th>
          </tr>
        </thead>
        <tbody>
          {atr.test_lines.length === 0 && (
            <tr><td colSpan={6}>No test lines.</td></tr>
          )}
          {atr.test_lines.map((line) => (
            <tr key={line.line_no}>
              <td>{line.line_no}</td>
              <td>{line.test_name ? `${line.test_name} (${line.test_code})` : line.test_code || `Test #${line.test_id}`}</td>
              <td>{line.specification || '-'}</td>
              <td>{line.raw_data_reference || '-'}</td>
              <td>{line.result || '-'}</td>
              <td>{line.remark || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h4 style={{ marginBottom: '0.25rem' }}>Approval Signature Chain</h4>
      <table className="atr-table" style={{ marginTop: '0.5rem' }}>
        <thead>
          <tr>
            <th>Initiated By</th>
            <th>Approved By (FDGL)</th>
            <th>Accepted By (ADGL)</th>
            <th>Analysed By</th>
            <th>Released By (ADGL)</th>
          </tr>
        </thead>
        <tbody>
          <tr style={{ height: '48px' }}>
            <td>{atr.signatures.initiated_by || '-'}</td>
            <td>{atr.signatures.approved_by || '-'}</td>
            <td>{atr.signatures.accepted_by || '-'}</td>
            <td>{atr.signatures.analysed_by || '-'}</td>
            <td>{atr.signatures.released_by || '-'}</td>
          </tr>
          <tr>
            <td>{fmtDateTime(atr.signatures.initiated_at)}</td>
            <td>{fmtDateTime(atr.signatures.approved_at)}</td>
            <td>{fmtDateTime(atr.signatures.accepted_at)}</td>
            <td>{fmtDateTime(atr.signatures.analysed_at)}</td>
            <td>{fmtDateTime(atr.signatures.released_at)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};
