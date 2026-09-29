/**
 * Main application layout — Sakai-style collapsible sidebar + topbar,
 * following the enterprise architecture UI standard (PrimeReact + PrimeFlex,
 * CSS-variable driven design tokens, compact density). Matches the Anti
 * Gravity LIMS module set (Sample Manager, Resource Manager, SAP, etc.)
 */
import { useRef, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Avatar } from 'primereact/avatar';
import { Badge } from 'primereact/badge';
import { Button } from 'primereact/button';
import { Menu } from 'primereact/menu';
import { Tooltip } from 'primereact/tooltip';
import { useAppDispatch, useAppSelector } from '@app/store';
import { logout } from '@features/authentication/store/authSlice';
import { useMenuPermissions } from '@core/rbac/usePermissions';

interface NavItem {
  label: string;
  icon: string;
  path: string;
  section: string;
  menuKey: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', icon: 'pi pi-th-large', path: '/dashboard', section: 'Main', menuKey: 'dashboard' },
  { label: 'Samples', icon: 'pi pi-filter', path: '/samples', section: 'Sample Manager', menuKey: 'samples' },
  { label: 'Products', icon: 'pi pi-box', path: '/products', section: 'Sample Manager', menuKey: 'products' },
  { label: 'Tests', icon: 'pi pi-list-check', path: '/tests', section: 'Sample Manager', menuKey: 'tests' },
  { label: 'Specifications', icon: 'pi pi-file-check', path: '/specifications', section: 'Sample Manager', menuKey: 'specifications' },
  { label: 'OOS Investigations', icon: 'pi pi-exclamation-triangle', path: '/oos', section: 'Sample Manager', menuKey: 'oos' },
  { label: 'Material Queue', icon: 'pi pi-inbox', path: '/mrn/queue', section: 'Material Requisition', menuKey: 'mrnQueue' },
  { label: 'My MRNs', icon: 'pi pi-clipboard', path: '/mrn', section: 'Material Requisition', menuKey: 'mrnWorkspace' },
  { label: 'Test Request Form', icon: 'pi pi-file-edit', path: '/trf', section: 'Test Request Form', menuKey: 'trf' },
  { label: 'Test Templates', icon: 'pi pi-calculator', path: '/test-templates', section: 'Test Request Form', menuKey: 'testTemplates' },
  { label: 'Certificates of Analysis', icon: 'pi pi-file-check', path: '/coa', section: 'Test Request Form', menuKey: 'coa' },
  { label: 'Instruments', icon: 'pi pi-cog', path: '/instruments', section: 'Resource Manager', menuKey: 'instruments' },
  { label: 'Stability', icon: 'pi pi-sun', path: '/stability', section: 'Resource Manager', menuKey: 'stability' },
  { label: 'Chemicals & Reagents', icon: 'pi pi-flask', path: '/chemicals', section: 'Resource Manager', menuKey: 'chemicals' },
  { label: 'Reference Standards', icon: 'pi pi-verified', path: '/standards', section: 'Resource Manager', menuKey: 'standards' },
  { label: 'Columns', icon: 'pi pi-bars', path: '/columns', section: 'Resource Manager', menuKey: 'columns' },
  { label: 'Volumetric Solutions', icon: 'pi pi-tint', path: '/volumetric', section: 'Resource Manager', menuKey: 'volumetric' },
  { label: 'SAP Integration', icon: 'pi pi-sitemap', path: '/sap', section: 'Integration', menuKey: 'sap' },
  { label: 'User Management', icon: 'pi pi-users', path: '/users', section: 'Administration', menuKey: 'users' },
  { label: 'Audit Trail', icon: 'pi pi-history', path: '/audit', section: 'Administration', menuKey: 'audit' },
];

export const MainLayout = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAppSelector((state) => state.auth);
  const userMenu = useRef<Menu>(null);
  const { menuKeys, isLoaded } = useMenuPermissions();
  const [collapsed, setCollapsed] = useState(false);

  const visibleItems = NAV_ITEMS.filter((item) => (isLoaded ? menuKeys.includes(item.menuKey) : false));

  const sections = visibleItems.reduce<Record<string, NavItem[]>>((acc, item) => {
    (acc[item.section] ??= []).push(item);
    return acc;
  }, {});

  const currentPage = NAV_ITEMS.find((i) => i.path === location.pathname)?.label || '';
  const sidebarWidth = collapsed ? '60px' : '220px';

  const userMenuItems = [
    { label: user?.full_name || user?.username, icon: 'pi pi-user', disabled: true },
    { separator: true },
    { label: 'Logout', icon: 'pi pi-sign-out', command: () => { dispatch(logout()); navigate('/login'); } },
  ];

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--color-surface-ground)' }}>
      {/* ─── Sidebar ─── */}
      <aside
        className="em-sidebar flex-shrink-0 flex flex-column transition-all transition-duration-200"
        style={{ width: sidebarWidth, minHeight: '100vh', overflow: 'hidden' }}
        aria-label="Sidebar navigation"
      >
        <div
          className="flex align-items-center justify-content-between px-3"
          style={{ height: '48px', borderBottom: '1px solid var(--color-surface-border)' }}
        >
          {!collapsed && (
            <span className="font-bold text-lg" style={{ color: 'var(--color-primary)' }}>
              ANTI GRAVITY
            </span>
          )}
          <Button
            icon={collapsed ? 'pi pi-angle-right' : 'pi pi-angle-left'}
            rounded
            text
            severity="secondary"
            size="small"
            onClick={() => setCollapsed(!collapsed)}
            aria-label="Toggle sidebar"
            style={{ minWidth: '1.75rem', height: '1.75rem' }}
          />
        </div>

        <nav className="flex-1 overflow-y-auto py-2 px-1">
          {Object.entries(sections).map(([section, items]) => (
            <div key={section} className="mb-2">
              {!collapsed && (
                <div
                  className="text-xs font-semibold uppercase mb-1 px-2"
                  style={{ color: 'var(--color-text-muted)', letterSpacing: '0.05em', fontSize: '0.6rem' }}
                >
                  {section}
                </div>
              )}
              {items.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <button
                    key={item.path}
                    onClick={() => navigate(item.path)}
                    className={`w-full flex align-items-center gap-2 border-none cursor-pointer transition-colors transition-duration-200 ${collapsed ? 'justify-content-center px-1 py-2' : 'px-2 py-2'} mb-1`}
                    style={{
                      background: isActive ? 'var(--color-primary-50)' : 'transparent',
                      borderRadius: 'var(--radius-md)',
                      borderLeft: !collapsed ? (isActive ? '3px solid var(--color-primary)' : '3px solid transparent') : undefined,
                      color: isActive ? 'var(--color-primary)' : 'var(--color-text-primary)',
                      fontWeight: isActive ? 600 : 400,
                      fontSize: '12px',
                    }}
                    aria-label={item.label}
                    aria-current={isActive ? 'page' : undefined}
                    data-pr-tooltip={collapsed ? item.label : undefined}
                    data-pr-position="right"
                  >
                    <i
                      className={item.icon}
                      style={{
                        fontSize: collapsed ? '1.1rem' : '0.85rem',
                        color: isActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                      }}
                    />
                    {!collapsed && <span>{item.label}</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="p-3" style={{ borderTop: '1px solid var(--color-surface-border)' }}>
          <div className="flex align-items-center gap-2">
            <Avatar
              label={user?.full_name?.charAt(0).toUpperCase() || 'U'}
              shape="circle"
              style={{ background: 'var(--color-primary)', color: '#fff' }}
            />
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium m-0" style={{ color: 'var(--color-text-primary)' }}>{user?.full_name}</p>
                <p className="text-xs m-0" style={{ color: 'var(--color-text-muted)' }}>{user?.role}</p>
              </div>
            )}
          </div>
        </div>
      </aside>

      {collapsed && <Tooltip target="[data-pr-tooltip]" />}

      {/* ─── Main Content Area ─── */}
      <div className="flex-1 flex flex-column" style={{ minWidth: 0 }}>
        <header className="em-topbar flex align-items-center justify-content-between px-3" style={{ height: '48px' }} aria-label="Top bar">
          <div className="flex align-items-center gap-2">
            <span className="text-600" style={{ fontSize: '12px' }}>
              <i className="pi pi-home" style={{ fontSize: '11px' }} />
            </span>
            {currentPage && (
              <>
                <span className="text-400" style={{ fontSize: '11px' }}>/</span>
                <span className="font-medium" style={{ fontSize: '12px', color: 'var(--color-text-primary)' }}>
                  {currentPage}
                </span>
              </>
            )}
          </div>

          <div className="flex align-items-center gap-2">
            <Button
              icon="pi pi-bell"
              rounded
              text
              severity="secondary"
              aria-label="Notifications"
              className="p-overlay-badge"
              style={{ width: '2rem', height: '2rem' }}
            >
              <Badge value="0" severity="danger" style={{ fontSize: '0.6rem', minWidth: '1rem', height: '1rem', lineHeight: '1rem' }} />
            </Button>

            <Menu model={userMenuItems} popup ref={userMenu} />
            <Button
              rounded
              text
              onClick={(e) => userMenu.current?.toggle(e)}
              aria-label="User menu"
              className="flex align-items-center gap-1"
              style={{ padding: '0.25rem' }}
            >
              <Avatar
                label={user?.full_name?.charAt(0).toUpperCase() || 'U'}
                shape="circle"
                size="normal"
                style={{ background: 'var(--color-primary)', color: '#fff', width: '1.75rem', height: '1.75rem', fontSize: '0.75rem' }}
              />
              <span className="hidden lg:inline font-medium" style={{ color: 'var(--color-text-primary)', fontSize: '12px' }}>
                {user?.username}
              </span>
            </Button>
          </div>
        </header>

        <main className="flex-1 p-3 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
