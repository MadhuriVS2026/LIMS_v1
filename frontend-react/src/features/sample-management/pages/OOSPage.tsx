/**
 * OOS Investigations page — root cause + CAPA closure workflow.
 */
import { useState } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputTextarea } from 'primereact/inputtextarea';
import { InputText } from 'primereact/inputtext';
import { StatusBadge } from '@shared/components/StatusBadge';
import { toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useCloseOOS, useOOSList } from '../hooks/useSamples';
import type { OOSInvestigation } from '../models/oos.types';

export const OOSPage = () => {
  const { data: oosRecords = [], isLoading } = useOOSList();
  const closeOOS = useCloseOOS();
  const { hasRole } = usePermissions();

  const [target, setTarget] = useState<OOSInvestigation | null>(null);
  const [rootCause, setRootCause] = useState('');
  const [correctiveAction, setCorrectiveAction] = useState('');
  const [password, setPassword] = useState('');

  const handleClose = () => {
    if (!target) return;
    if (!rootCause.trim() || !correctiveAction.trim() || !password) {
      toastService.warn('Root cause, corrective action, and password are required.', 'Missing fields');
      return;
    }
    closeOOS.mutate(
      { id: target.id, rootCause, correctiveAction, password },
      {
        onSuccess: () => {
          toastService.success(`OOS #${target.id} closed with root cause and CAPA.`, 'Investigation Closed');
          setTarget(null);
          setRootCause('');
          setCorrectiveAction('');
          setPassword('');
        },
      }
    );
  };

  return (
    <div>
      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={oosRecords} loading={isLoading} paginator rows={10} size="small">
          <Column header="ID" body={(row) => `#${row.id}`} />
          <Column header="Test" body={(row) => row.test?.name} />
          <Column header="Phase 1 Comments" body={(row) => <span className="text-sm">{row.phase1_comments}</span>} />
          <Column header="Status" body={(row) => <StatusBadge status={row.status} />} />
          <Column header="Created" body={(row) => new Date(row.created_date).toLocaleDateString()} />
          <Column
            header="Actions"
            body={(row) =>
              row.status === 'Open' && hasRole('Supervisor', 'QA') ? (
                <Button label="Close" size="small" text onClick={() => setTarget(row)} />
              ) : null
            }
          />
        </DataTable>
      </div>

      <Dialog header="Close OOS Investigation" visible={!!target} onHide={() => setTarget(null)} style={{ width: '460px' }} modal>
        <div className="flex flex-column gap-3">
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Root Cause</label>
            <InputTextarea value={rootCause} onChange={(e) => setRootCause(e.target.value)} rows={3} className="w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Corrective Action</label>
            <InputTextarea value={correctiveAction} onChange={(e) => setCorrectiveAction(e.target.value)} rows={3} className="w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Password (E-Sign)</label>
            <InputText type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full" />
          </div>
          <Button
            label="Close Investigation"
            onClick={handleClose}
            loading={closeOOS.isPending}
            disabled={!rootCause || !correctiveAction || !password}
            className="w-full mt-1"
          />
        </div>
      </Dialog>
    </div>
  );
};
