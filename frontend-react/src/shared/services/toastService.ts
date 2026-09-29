/**
 * Global toast service — allows showing success/error notifications from
 * anywhere (mutation onError/onSuccess callbacks, API interceptors, etc.)
 * without prop-drilling a Toast ref through every component.
 *
 * Mounted once via <ToastHost /> in App.tsx.
 */
import { Toast } from 'primereact/toast';
import { createRef } from 'react';

export const toastRef = createRef<Toast>();

function show(severity: 'success' | 'info' | 'warn' | 'error', summary: string, detail?: string) {
  toastRef.current?.show({ severity, summary, detail, life: 4000 });
}

export const toastService = {
  success: (detail: string, summary = 'Success') => show('success', summary, detail),
  info: (detail: string, summary = 'Info') => show('info', summary, detail),
  warn: (detail: string, summary = 'Warning') => show('warn', summary, detail),
  error: (detail: string, summary = 'Error') => show('error', summary, detail),
};

/** Extracts a human-readable message from an Axios/FastAPI error response. */
export function getErrorMessage(error: unknown): string {
  const anyErr = error as any;
  return (
    anyErr?.response?.data?.detail ||
    anyErr?.message ||
    'An unexpected error occurred. Please try again.'
  );
}
