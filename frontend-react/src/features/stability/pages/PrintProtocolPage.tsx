/**
 * Printable Stability Protocol — laid out to match the real "Stability
 * Protocol Format" Word document (header block, API/Pack details, the
 * Loading Matrix as a condition x time-point grid, and a 3-signature
 * footer: Prepared By / Checked By (Formulation) / Checked By
 * (Analytical)). Rendered standalone so browser Print -> Save as PDF
 * produces a clean document.
 */
import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from 'primereact/button';
import { useMatrix, useProtocolDetail } from '../hooks/useStability';
import { STANDARD_TIME_POINT_DAYS } from '../models/stability.types';

const fmtDate = (value?: string | null) => (value ? new Date(value).toLocaleDateString() : '-');

export const PrintProtocolPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const protocolId = Number(id);
  const { data: protocol, isLoading } = useProtocolDetail(protocolId);
  const { data: matrixCells = [] } = useMatrix(protocolId);

  useEffect(() => {
    document.title = protocol ? `Stability Protocol - ${protocol.protocol_code}` : 'Stability Protocol';
  }, [protocol]);

  if (isLoading || !protocol) {
    return <p style={{ padding: '2rem' }}>Loading protocol...</p>;
  }

  const conditions = Array.from(new Set(matrixCells.map((c) => c.condition)));
  const cellFor = (condition: string, isReserve: boolean, day: number | null) =>
    matrixCells.find((c) => c.condition === condition && c.is_reserve === isReserve && c.time_point_days === day);

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
        table.stab-table { width: 100%; border-collapse: collapse; font-size: 11px; }
        table.stab-table th, table.stab-table td { border: 1px solid #333; padding: 4px 6px; text-align: center; }
        table.stab-table th { background: #f0f0f0; }
        td.label-cell, th.label-cell { text-align: left; }
      `}</style>

      <div style={{ textAlign: 'center', borderBottom: '2px solid #000', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0 }}>EMCURE</h2>
        <p style={{ margin: 0 }}>R&amp;D Ahmedabad</p>
        <p style={{ margin: 0, fontWeight: 'bold' }}>STABILITY PROTOCOL — LIQUID DOSAGE FORM</p>
        <p style={{ margin: 0, fontSize: '12px' }}>Protocol No.: {protocol.protocol_code}</p>
      </div>

      <table className="stab-table" style={{ marginBottom: '1rem' }}>
        <tbody>
          <tr><td className="label-cell"><strong>Product Name</strong></td><td className="label-cell">{protocol.label_claim || '-'}</td><td className="label-cell"><strong>Label Claim</strong></td><td className="label-cell">{protocol.label_claim || '-'}</td></tr>
          <tr><td className="label-cell"><strong>Mfg. Date</strong></td><td className="label-cell">{fmtDate(protocol.mfg_date)}</td><td className="label-cell"><strong>Batch No.</strong></td><td className="label-cell">{protocol.batch_number || '-'}</td></tr>
          <tr><td className="label-cell"><strong>Placebo Batch No.</strong></td><td className="label-cell">{protocol.placebo_batch_number || '-'}</td><td className="label-cell"><strong>Batch Size</strong></td><td className="label-cell">{protocol.batch_size || '-'}</td></tr>
          <tr><td className="label-cell"><strong>Stability Initiation Date</strong></td><td className="label-cell">{fmtDate(protocol.stability_initiation_date)}</td><td className="label-cell"><strong>No. of Samples / Time Points</strong></td><td className="label-cell">{protocol.no_of_samples_time_points || '-'}</td></tr>
          <tr><td className="label-cell"><strong>Fill Volume</strong></td><td className="label-cell">{protocol.fill_volume || '-'}</td><td className="label-cell"><strong>Study Type</strong></td><td className="label-cell">{protocol.study_type || '-'}</td></tr>
          <tr><td className="label-cell"><strong>API Name</strong></td><td className="label-cell">{protocol.api_name || '-'}</td><td className="label-cell"><strong>API Batch No.</strong></td><td className="label-cell">{protocol.api_batch_no || '-'}</td></tr>
          <tr><td className="label-cell"><strong>API Source</strong></td><td className="label-cell">{protocol.api_source || '-'}</td><td className="label-cell"><strong>Duration</strong></td><td className="label-cell">{protocol.duration_months} months</td></tr>
          <tr><td className="label-cell"><strong>Primary Pack</strong></td><td className="label-cell">{protocol.primary_pack || '-'}</td><td className="label-cell"><strong>Secondary Pack</strong></td><td className="label-cell">{protocol.secondary_pack || '-'}</td></tr>
          <tr><td className="label-cell"><strong>Headspace</strong></td><td className="label-cell">{protocol.headspace || '-'}</td><td className="label-cell"><strong>Orientation</strong></td><td className="label-cell">{protocol.orientation || '-'}</td></tr>
        </tbody>
      </table>

      <h4 style={{ marginBottom: '0.25rem' }}>Loading Matrix</h4>
      <table className="stab-table" style={{ marginBottom: '1rem' }}>
        <thead>
          <tr>
            <th className="label-cell">Stability Condition / Time Points (Days)</th>
            {STANDARD_TIME_POINT_DAYS.map((day) => (
              <th key={day}>{day}</th>
            ))}
            <th>Reserve</th>
          </tr>
        </thead>
        <tbody>
          {conditions.length === 0 && (
            <tr><td colSpan={STANDARD_TIME_POINT_DAYS.length + 2}>No Loading Matrix defined.</td></tr>
          )}
          {conditions.map((condition) => (
            <tr key={condition}>
              <td className="label-cell">{condition}</td>
              {STANDARD_TIME_POINT_DAYS.map((day) => {
                const cell = cellFor(condition, false, day);
                return <td key={day}>{cell?.is_scheduled ? '✓' : ''}</td>;
              })}
              <td>{cellFor(condition, true, null)?.is_scheduled ? '✓' : ''}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p style={{ fontSize: '12px' }}><strong>Remarks:</strong> {protocol.remarks || ''}</p>

      <table className="stab-table" style={{ marginTop: '2rem' }}>
        <thead>
          <tr>
            <th>Prepared By</th>
            <th>Checked By (R&amp;D Formulation)</th>
            <th>Checked By (R&amp;D Analytical)</th>
          </tr>
        </thead>
        <tbody>
          <tr style={{ height: '48px' }}>
            <td>{protocol.created_by}</td>
            <td>{protocol.formulation_checked_by || ''}</td>
            <td>{protocol.approved_by || ''}</td>
          </tr>
          <tr>
            <td>{fmtDate(protocol.created_date)}</td>
            <td>{fmtDate(protocol.formulation_checked_at)}</td>
            <td>{fmtDate(protocol.approved_at)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};
