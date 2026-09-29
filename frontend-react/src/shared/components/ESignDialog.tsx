/**
 * Electronic Signature confirmation dialog — re-verifies the user's password
 * before any GxP-critical action (approvals, releases, submissions).
 */
import { useState } from 'react';
import { Dialog } from 'primereact/dialog';
import { Password } from 'primereact/password';
import { InputTextarea } from 'primereact/inputtextarea';
import { Button } from 'primereact/button';

interface ESignDialogProps {
  visible: boolean;
  title?: string;
  actionLabel?: string;
  showComments?: boolean;
  loading?: boolean;
  onHide: () => void;
  onConfirm: (password: string, comments?: string) => void;
}

export const ESignDialog = ({
  visible,
  title = 'Electronic Signature Required',
  actionLabel = 'Confirm',
  showComments = true,
  loading = false,
  onHide,
  onConfirm,
}: ESignDialogProps) => {
  const [password, setPassword] = useState('');
  const [comments, setComments] = useState('');

  const handleConfirm = () => {
    onConfirm(password, comments || undefined);
    setPassword('');
    setComments('');
  };

  return (
    <Dialog header={title} visible={visible} onHide={onHide} style={{ width: '420px' }} modal>
      <div className="flex flex-column gap-3">
        <p className="text-sm text-600 m-0">
          Re-enter your password to electronically sign this action, per 21 CFR Part 11.
        </p>
        <div>
          <label className="block text-sm font-medium text-700 mb-1">Password</label>
          <Password
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full"
            inputClassName="w-full"
            feedback={false}
            autoFocus
          />
        </div>
        {showComments && (
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Comments (optional)</label>
            <InputTextarea value={comments} onChange={(e) => setComments(e.target.value)} rows={2} className="w-full" />
          </div>
        )}
        <Button label={actionLabel} onClick={handleConfirm} loading={loading} disabled={!password} className="w-full mt-1" />
      </div>
    </Dialog>
  );
};
