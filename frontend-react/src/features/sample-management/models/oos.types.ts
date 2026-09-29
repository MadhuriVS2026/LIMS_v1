import type { TestParameter } from './sample.types';

export interface OOSInvestigation {
  id: number;
  sample_id: number;
  test_id: number;
  investigation_type?: string;
  phase1_comments: string;
  root_cause?: string | null;
  corrective_action?: string | null;
  status: string;
  created_by: string;
  created_date: string;
  closed_by?: string | null;
  closed_at?: string | null;
  test?: TestParameter;
}
