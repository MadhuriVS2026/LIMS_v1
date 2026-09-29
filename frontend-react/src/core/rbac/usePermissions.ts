/**
 * Role-based access control hook.
 * Anti Gravity LIMS uses a simple 4-role model (Admin, Analyst, Supervisor, QA)
 * rather than granular permission codes, but the hook shape matches the
 * enterprise reference architecture for consistency and future extension.
 */
import { useAppSelector } from '@app/store';

export type Role = 'Admin' | 'Analyst' | 'Supervisor' | 'QA';

const MENU_ACCESS: Record<string, Role[]> = {
  dashboard: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  samples: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  products: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  tests: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  specifications: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  oos: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  mrnQueue: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  mrnWorkspace: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  trf: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  //  Readable by everyone — an analyst needs to see which template produced a
  //  result. Authoring inside the pages is Admin-only, enforced by the backend.
  testTemplates: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  //  Likewise: anyone may read a certificate their results went into. Issuing one
  //  is QA/Admin, enforced by the backend.
  coa: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  instruments: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  stability: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  chemicals: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  standards: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  columns: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  volumetric: ['Admin', 'Analyst', 'Supervisor', 'QA'],
  sap: ['Admin', 'QA', 'Analyst'],
  users: ['Admin'],
  audit: ['Admin', 'Analyst', 'Supervisor', 'QA'],
};

export function usePermissions() {
  const role = useAppSelector((state) => state.auth.user?.role) as Role | undefined;
  //  Exposed because several rules are ownership-based rather than role-based —
  //  e.g. only the uploader of an attachment may remove it.
  const username = useAppSelector((state) => state.auth.user?.username);

  const hasRole = (...roles: Role[]): boolean => (role ? roles.includes(role) : false);

  const canAccessMenu = (menuKey: string): boolean => {
    if (!role) return false;
    const allowed = MENU_ACCESS[menuKey];
    return allowed ? allowed.includes(role) : true;
  };

  return { role, username, hasRole, canAccessMenu, isLoaded: !!role };
}

export function useMenuPermissions() {
  const role = useAppSelector((state) => state.auth.user?.role) as Role | undefined;
  const menuKeys = Object.keys(MENU_ACCESS).filter((key) => (role ? MENU_ACCESS[key].includes(role) : false));
  return { menuKeys, isLoaded: !!role };
}
