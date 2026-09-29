/**
 * Audit Trail page — 21 CFR Part 11 compliance log viewer.
 */
import { useQuery } from '@tanstack/react-query';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { auditApi } from '../api/auditApi';

export const AuditPage = () => {
  const { data: logs = [], isLoading } = useQuery({ queryKey: ['audit-logs'], queryFn: () => auditApi.list(50) });

  return (
    <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
      <DataTable value={logs} loading={isLoading} paginator rows={15} size="small">
        <Column header="Timestamp" body={(row) => new Date(row.timestamp).toLocaleString()} />
        <Column field="username" header="User" />
        <Column header="Action" body={(row) => <span className="font-mono text-xs">{row.action}</span>} />
        <Column field="table_name" header="Table" />
        <Column header="Record" body={(row) => `#${row.record_id ?? '-'}`} />
        <Column header="Comments" body={(row) => <span className="text-xs text-500">{row.comments || '-'}</span>} />
      </DataTable>
    </div>
  );
};
