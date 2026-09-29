/**
 * Dashboard page — real-time KPI overview and quick actions.
 */
import { useNavigate } from 'react-router-dom';
import { ProgressSpinner } from 'primereact/progressspinner';
import { useDashboardStats } from '../hooks/useDashboardStats';
import { StatCard } from '../components/StatCard';

export const DashboardPage = () => {
  const navigate = useNavigate();
  const { data: stats, isLoading } = useDashboardStats();

  if (isLoading || !stats) {
    return (
      <div className="flex justify-content-center py-8">
        <ProgressSpinner style={{ width: '40px', height: '40px' }} />
      </div>
    );
  }

  const quickActions = [
    { label: 'Log New Sample', path: '/samples', color: '#2563eb', bg: '#eff6ff' },
    { label: 'View Instruments', path: '/instruments', color: '#16a34a', bg: '#f0fdf4' },
    { label: 'OOS Cases', path: '/oos', color: '#dc2626', bg: '#fef2f2' },
    { label: 'SAP Interface', path: '/sap', color: '#7c3aed', bg: '#faf5ff' },
  ];

  return (
    <div>
      <div className="grid mb-4">
        <div className="col-12 md:col-6 lg:col-3">
          <StatCard label="Total Samples" value={stats.total_samples} icon="pi pi-filter" color="#2563eb" />
        </div>
        <div className="col-12 md:col-6 lg:col-3">
          <StatCard label="Pending Review" value={stats.pending_reviews} icon="pi pi-clock" color="#d97706" />
        </div>
        <div className="col-12 md:col-6 lg:col-3">
          <StatCard label="OOS Open" value={stats.oos_open} icon="pi pi-exclamation-triangle" color="#dc2626" />
        </div>
        <div className="col-12 md:col-6 lg:col-3">
          <StatCard label="Calibration Due" value={stats.instruments_due_calibration} icon="pi pi-wrench" color="#ea580c" />
        </div>
      </div>

      <div className="grid">
        <div className="col-12 lg:col-6">
          <div className="bg-white border-round-lg p-4 border-1 border-200 h-full">
            <h3 className="text-base font-semibold text-900 mt-0 mb-3">Today's Activity</h3>
            <div className="flex flex-column gap-3">
              <div className="flex justify-content-between align-items-center">
                <span className="text-sm text-600">Samples Logged</span>
                <span className="font-semibold text-900">{stats.samples_today}</span>
              </div>
              <div className="flex justify-content-between align-items-center">
                <span className="text-sm text-600">Batches Approved</span>
                <span className="font-semibold" style={{ color: '#16a34a' }}>{stats.approved_today}</span>
              </div>
              <div className="flex justify-content-between align-items-center">
                <span className="text-sm text-600">Batches Rejected</span>
                <span className="font-semibold" style={{ color: '#dc2626' }}>{stats.rejected_today}</span>
              </div>
              <div className="flex justify-content-between align-items-center">
                <span className="text-sm text-600">Pending Samples</span>
                <span className="font-semibold" style={{ color: '#d97706' }}>{stats.pending_samples}</span>
              </div>
            </div>
          </div>
        </div>
        <div className="col-12 lg:col-6">
          <div className="bg-white border-round-lg p-4 border-1 border-200 h-full">
            <h3 className="text-base font-semibold text-900 mt-0 mb-3">Quick Actions</h3>
            <div className="grid">
              {quickActions.map((action) => (
                <div key={action.path} className="col-6">
                  <button
                    onClick={() => navigate(action.path)}
                    className="w-full p-3 border-none border-round-lg cursor-pointer text-sm font-medium transition-colors"
                    style={{ background: action.bg, color: action.color }}
                  >
                    {action.label}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
