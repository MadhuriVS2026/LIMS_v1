/**
 * Printable Stability Report — laid out to match the real "Stability Report
 * Format" Word document (Product/Composition/Batch header block, a
 * test-vs-timepoint results table, remarks, and a 4-signature footer:
 * Prepared/Checked/Reviewed/Approved By). Rendered standalone (no
 * MainLayout sidebar/topbar) so browser Print -> Save as PDF produces a
 * clean document. Opened via a "Print" action from the report's View dialog.
 */
import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from 'primereact/button';
import { useReportDetail } from '../hooks/useStability';

const fmtDate = (value?: string | null) => (value ? new Date(value).toLocaleDateString() : '-');

export const PrintReportPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: report, isLoading } = useReportDetail(Number(id));

  useEffect(() => {
    document.title = report ? `Stability Report - ${report.report_number}` : 'Stability Report';
  }, [report]);

  if (isLoading || !report) {
    return <p style={{ padding: '2rem' }}>Loading report...</p>;
  }

  const timePointLabels = Array.from(
    new Set(report.results_data.flatMap((row) => Object.keys(row.results || {})))
  );

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '2rem', fontFamily: 'Arial, sans-serif', color: '#111' }}>
      <div className="no-print" style={{ marginBottom: '1rem', display: 'flex', gap: '0.5rem' }}>
        <Button label="Back" icon="pi pi-arrow-left" text onClick={() => navigate(-1)} />
        <Button label="Print / Save as PDF" icon="pi pi-print" onClick={() => window.print()} />
      </div>

      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { margin: 0; }
        }
        table.stab-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        table.stab-table th, table.stab-table td { border: 1px solid #333; padding: 6px 8px; text-align: left; }
        table.stab-table th { background: #f0f0f0; }
      `}</style>

      <div style={{ textAlign: 'center', borderBottom: '2px solid #000', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0 }}>EMCURE</h2>
        <p style={{ margin: 0 }}>Stability Study Data</p>
        <p style={{ margin: 0, fontSize: '12px' }}>Report No.: {report.report_number}</p>
      </div>

      <table className="stab-table" style={{ marginBottom: '1rem' }}>
        <tbody>
          <tr><td><strong>Product Name</strong></td><td>{report.product_name || '-'}</td><td><strong>Batch No.</strong></td><td>{report.batch_no || '-'}</td></tr>
          <tr><td><strong>Composition / Label</strong></td><td>{report.composition_label || '-'}</td><td><strong>Batch Size</strong></td><td>{report.batch_size || '-'}</td></tr>
          <tr><td><strong>Manufactured At</strong></td><td>{report.manufactured_at || '-'}</td><td><strong>Manufacturing Date</strong></td><td>{fmtDate(report.manufacturing_date)}</td></tr>
          <tr><td><strong>Stability Study Type</strong></td><td>{report.stability_study_type || '-'}</td><td><strong>Expiry Date</strong></td><td>{fmtDate(report.expiry_date)}</td></tr>
          <tr><td><strong>Stability Condition</strong></td><td>{report.stability_condition || '-'}</td><td><strong>Stability Protocol No.</strong></td><td>{report.stability_protocol_no || '-'}</td></tr>
          <tr><td><strong>Date of Commencement</strong></td><td>{fmtDate(report.date_of_commencement)}</td><td><strong>API Source</strong></td><td>{report.api_source || '-'}</td></tr>
          <tr><td><strong>API Batch Number</strong></td><td>{report.api_batch_number || '-'}</td><td><strong>Packing</strong></td><td>{report.packing || '-'}</td></tr>
        </tbody>
      </table>

      <table className="stab-table" style={{ marginBottom: '1rem' }}>
        <thead>
          <tr>
            <th>Sr. No.</th>
            <th>Tests</th>
            <th>Stability Specification</th>
            {timePointLabels.map((label) => (
              <th key={label}>{label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {report.results_data.length === 0 && (
            <tr><td colSpan={3 + timePointLabels.length} style={{ textAlign: 'center' }}>No completed time points yet.</td></tr>
          )}
          {report.results_data.map((row, idx) => (
            <tr key={row.test_id}>
              <td>{idx + 1}.</td>
              <td>{row.test_name}</td>
              <td>{row.specification}</td>
              {timePointLabels.map((label) => (
                <td key={label}>{String(row.results?.[label] ?? '-')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <p style={{ fontSize: '12px' }}><strong>Remarks:</strong> {report.remarks || ''}</p>

      <table className="stab-table" style={{ marginTop: '2rem' }}>
        <thead>
          <tr>
            <th>Prepared By</th>
            <th>Checked By</th>
            <th>Reviewed By</th>
            <th>Approved By</th>
          </tr>
        </thead>
        <tbody>
          <tr style={{ height: '48px' }}>
            <td>{report.prepared_by || ''}</td>
            <td>{report.checked_by_name || ''}</td>
            <td>{report.reviewed_by_name || ''}</td>
            <td>{report.approved_by || ''}</td>
          </tr>
          <tr>
            <td>{fmtDate(report.prepared_at)}</td>
            <td></td>
            <td></td>
            <td>{fmtDate(report.approved_at)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};
