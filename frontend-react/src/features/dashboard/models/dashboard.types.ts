export interface DashboardStats {
  total_samples: number;
  pending_samples: number;
  oos_open: number;
  samples_today: number;
  instruments_due_calibration: number;
  pending_reviews: number;
  approved_today: number;
  rejected_today: number;
}
