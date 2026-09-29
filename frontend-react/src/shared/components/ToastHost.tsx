/**
 * Mounts the single app-wide Toast instance, wired to toastService's ref.
 */
import { Toast } from 'primereact/toast';
import { toastRef } from '@shared/services/toastService';

export const ToastHost = () => <Toast ref={toastRef} position="top-right" />;
