/**
 * PermissionGate — conditionally renders children based on the current user's role.
 */
import { ReactNode } from 'react';
import { usePermissions, Role } from './usePermissions';

interface PermissionGateProps {
  roles: Role[];
  children: ReactNode;
  fallback?: ReactNode;
}

export const PermissionGate = ({ roles, children, fallback = null }: PermissionGateProps) => {
  const { hasRole } = usePermissions();
  return hasRole(...roles) ? <>{children}</> : <>{fallback}</>;
};
