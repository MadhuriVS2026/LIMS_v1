interface StatCardProps {
  label: string;
  value: number | string;
  icon: string;
  color: string;
}

export const StatCard = ({ label, value, icon, color }: StatCardProps) => (
  <div className="bg-white border-round-lg p-4 border-1 border-200 flex align-items-center justify-content-between">
    <div>
      <p className="text-sm text-500 m-0 mb-1">{label}</p>
      <p className="text-2xl font-bold text-900 m-0">{value}</p>
    </div>
    <div
      className="flex align-items-center justify-content-center border-round-lg"
      style={{ width: '2.5rem', height: '2.5rem', background: `${color}1A` }}
    >
      <i className={icon} style={{ color, fontSize: '1.2rem' }} />
    </div>
  </div>
);
