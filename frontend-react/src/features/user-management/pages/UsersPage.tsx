/**
 * User Management page (Admin only) — create users, toggle activation.
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { toastService } from '@shared/services/toastService';
import { userManagementApi } from '../api/userManagementApi';

const ROLES = ['Admin', 'Analyst', 'Supervisor', 'QA'];

export const UsersPage = () => {
  const qc = useQueryClient();
  const { data: users = [], isLoading } = useQuery({ queryKey: ['users'], queryFn: userManagementApi.list });
  const createUser = useMutation({
    mutationFn: userManagementApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });
  const toggleUser = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) => userManagementApi.update(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ username: '', password: '', full_name: '', role: 'Analyst', department: '' });

  const handleCreate = () => {
    if (!form.username || !form.password || !form.full_name) {
      toastService.warn('Username, password, and full name are required.', 'Missing fields');
      return;
    }
    createUser.mutate(form, {
      onSuccess: (user) => {
        toastService.success(`User ${user.username} created.`, 'User Created');
        setShowModal(false);
        setForm({ username: '', password: '', full_name: '', role: 'Analyst', department: '' });
      },
    });
  };

  const handleToggle = (id: number, username: string, nextActive: boolean) => {
    toggleUser.mutate(
      { id, is_active: nextActive },
      {
        onSuccess: () => toastService.success(`User ${username} ${nextActive ? 'activated' : 'deactivated'}.`, 'User Updated'),
      }
    );
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{users.length} users</p>
        <Button label="Add User" icon="pi pi-plus" onClick={() => setShowModal(true)} />
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={users} loading={isLoading} paginator rows={10} size="small">
          <Column field="username" header="Username" />
          <Column field="full_name" header="Full Name" />
          <Column field="role" header="Role" />
          <Column field="department" header="Department" />
          <Column header="Active" body={(row) => (row.is_active ? <span className="text-green-600">●</span> : <span className="text-red-600">●</span>)} />
          <Column
            header="Actions"
            body={(row) => (
              <Button
                label={row.is_active ? 'Deactivate' : 'Activate'}
                size="small"
                text
                severity={row.is_active ? 'danger' : 'success'}
                onClick={() => handleToggle(row.id, row.username, !row.is_active)}
              />
            )}
          />
        </DataTable>
      </div>

      <Dialog header="Add User" visible={showModal} onHide={() => setShowModal(false)} style={{ width: '440px' }} modal>
        <div className="flex flex-column gap-3">
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Username</label><InputText value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Password</label><InputText type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="w-full" /></div>
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Full Name</label>
            <InputText value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} className="w-full" />
          </div>
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Role</label><Dropdown value={form.role} options={ROLES} onChange={(e) => setForm({ ...form, role: e.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Department</label><InputText value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} className="w-full" /></div>
          </div>
          <Button label="Create User" onClick={handleCreate} loading={createUser.isPending} className="w-full mt-1" />
        </div>
      </Dialog>
    </div>
  );
};
