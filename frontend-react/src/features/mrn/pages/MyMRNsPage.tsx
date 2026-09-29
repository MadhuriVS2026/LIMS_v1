/**
 * MRN list page — shows all MRNs for Admin/Supervisor, and only the current
 * user's own MRNs otherwise. New MRNs are raised from the Material Queue
 * page (select lots there, set quantity/project code, and submit) — this
 * page is the resulting list + drill-in to each MRN's detail/editor.
 */
import { useNavigate } from 'react-router-dom';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { StatusBadge } from '@shared/components/StatusBadge';
import { usePermissions } from '@core/rbac/usePermissions';
import { useMRNList } from '../hooks/useMrn';
import type { MaterialRequisition } from '../models/mrn.types';

export const MyMRNsPage = () => {
  const navigate = useNavigate();
  const { hasRole } = usePermissions();
  const canCreate = hasRole('Admin', 'Analyst');
  const { data: mrns = [], isLoading } = useMRNList();

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{mrns.length} requisition(s)</p>
        {canCreate && (
          <Button
            label="Raise MRN from Material Queue"
            icon="pi pi-inbox"
            outlined
            onClick={() => navigate('/mrn/queue')}
          />
        )}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={mrns} loading={isLoading} paginator rows={10} size="small" emptyMessage="No Material Requisitions yet.">
          <Column field="mrn_number" header="MRN Number" body={(row: MaterialRequisition) => <span className="font-mono text-blue-600">{row.mrn_number}</span>} />
          <Column header="Status" body={(row: MaterialRequisition) => <StatusBadge status={row.status} />} />
          <Column header="Line Items" body={(row: MaterialRequisition) => row.line_items.length} />
          <Column field="created_by" header="Created By" />
          <Column header="Created" body={(row: MaterialRequisition) => (row.created_date ? new Date(row.created_date).toLocaleString() : '-')} />
          <Column header="Submitted" body={(row: MaterialRequisition) => (row.submitted_at ? new Date(row.submitted_at).toLocaleString() : '-')} />
          <Column
            header="Actions"
            body={(row: MaterialRequisition) => (
              <Button label="View" size="small" text onClick={() => navigate(`/mrn/${row.id}`)} />
            )}
          />
        </DataTable>
      </div>
    </div>
  );
};
