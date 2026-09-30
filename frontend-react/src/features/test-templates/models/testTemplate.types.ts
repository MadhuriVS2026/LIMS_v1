/**
 * Test template and worksheet types.
 *
 * The definition types mirror `src/domain/services/calculation/template_schema.py`
 * closely enough for the worksheet form to render any template generically —
 * that is the whole point of the archetype approach, so the UI must not contain
 * per-archetype branching.
 */

export type TemplateStatus = 'Draft' | 'PendingApproval' | 'Active' | 'Inactive';
export type WorksheetStatus =
  | 'InProgress'
  | 'PendingReview'
  | 'ReferredBack'
  | 'Confirmed';

export type GroupKind = 'singleton' | 'table' | 'sequence';
export type FieldKind = 'context' | 'input' | 'area' | 'calculated' | 'flag';
export type ValueType = 'number' | 'text' | 'date' | 'boolean';
export type RoundMode = 'none' | 'round' | 'trunc';
export type Severity = 'blocking' | 'advisory';
export type CriterionOperator = 'lte' | 'gte' | 'between' | 'eq';

export interface Rounding {
  mode?: RoundMode;
  digits?: number;
  digitsFrom?: string;
}

export interface FieldDef {
  key: string;
  kind: FieldKind;
  label?: string;
  type?: ValueType;
  unit?: string | null;
  /** CALCULATED only. */
  expression?: string;
  rounding?: Rounding;
  required?: boolean;
  default?: unknown;
  options?: string[];
  /** CONTEXT: dotted path into the context payload, e.g. `trf.batch_number`. */
  source?: string | null;
  overridable?: boolean;
  /** AREA: `ManualEntry` today; the Waters import will set `CDS_IMPORT`. */
  areaSource?: string;
}

export interface RowSpec {
  min?: number;
  max?: number;
  default?: number;
  labelFrom?: string;
}

/**
 * A summary line rendered under a table group: a computed value pulled from the
 * worksheet's `computed.values` by dotted `ref` (e.g. `stats.mean_std`). Lets a
 * table show its own Mean/SD/%RSD footer instead of only a separate stats card.
 */
export interface GroupFooterItem {
  label: string;
  /** Dotted path into computed.values, e.g. `stats.rsd_std`. */
  ref: string;
  unit?: string | null;
  rounding?: Rounding;
}

/**
 * A read-only header line rendered above a table group, showing values pulled
 * from the worksheet's context (auto-fetched from the TRF/product). Used to
 * surface batch/AR/TRF/stability details as a summary row above a table,
 * without repeating them on every editable row.
 */
export interface GroupHeaderContextItem {
  label: string;
  /** Context field key, e.g. `batch_no` or `stability_condition`. */
  ref: string;
}

export interface GroupDef {
  key: string;
  kind: GroupKind;
  label?: string;
  rows?: RowSpec;
  fields: FieldDef[];
  /** Optional computed summary shown directly beneath the table. */
  footer?: GroupFooterItem[];
  /** Optional read-only context summary shown directly above the table. */
  headerContext?: GroupHeaderContextItem[];
}

export interface CriterionDef {
  key: string;
  label?: string;
  target: string;
  operator: CriterionOperator;
  limit: number | number[];
  severity?: Severity;
  limitText?: string;
}

export interface TemplateDefinition {
  context?: FieldDef[];
  groups?: GroupDef[];
  criteria?: CriterionDef[];
  /** Dotted `group.field` reference to the reportable result. */
  resultRef?: string | null;
}

export interface TestTemplateSummary {
  id: number;
  code: string;
  name: string;
  archetype: string;
  test_id: number;
  test_code?: string | null;
  test_name?: string | null;
  version: number;
  status: TemplateStatus;
  result_unit?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  superseded_by_id?: number | null;
  created_by?: string | null;
  created_date?: string | null;
}

export interface TestTemplate extends TestTemplateSummary {
  definition: TemplateDefinition;
  modified_by?: string | null;
  modified_date?: string | null;
}

export interface CreateTemplateRequest {
  name: string;
  archetype: string;
  test_id: number;
  result_unit?: string | null;
  definition: TemplateDefinition;
}

export interface UpdateDefinitionRequest {
  definition: TemplateDefinition;
}

export interface UpdateTemplateHeaderRequest {
  name?: string | null;
  result_unit?: string | null;
}

export interface EsignActionRequest {
  password: string;
  comments?: string | null;
}

// ── Worksheets ───────────────────────────────────────────────────────

/** A row of a group's stored values. Calculated columns are absent here. */
export type WorksheetRow = Record<string, unknown>;

export interface CriterionResult {
  key: string;
  label: string;
  observed: unknown;
  operator: CriterionOperator;
  limit: number[];
  limit_text: string;
  severity: Severity;
  /**
   * `null` means "not yet assessable" — the observed value is still blank.
   * That is distinct from failing, and must not be rendered as a failure.
   */
  passed: boolean | null;
}

export interface WorksheetComputed {
  /** Context scalars and singleton-group fields, keyed `group.field`. */
  values: Record<string, unknown>;
  /** Every group's rows, including calculated columns. */
  rows: Record<string, WorksheetRow[]>;
  criteria: CriterionResult[];
  reportable_result: unknown;
  has_blocking_failure: boolean;
}

export interface Worksheet {
  id: number;
  trf_test_line_id: number;
  template_id: number;
  template_version: number;
  template_code?: string | null;
  template_name?: string | null;
  status: WorksheetStatus;
  context_values: Record<string, unknown>;
  group_values: Record<string, WorksheetRow[]>;
  computed_snapshot?: Record<string, unknown> | null;
  reportable_result?: string | null;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  submitted_for_review_by?: string | null;
  submitted_for_review_at?: string | null;
  submission_comments?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  review_comments?: string | null;
  created_by?: string | null;
  created_date?: string | null;
  modified_by?: string | null;
  modified_date?: string | null;
}

/** Worksheet + bound definition + current computed state, in one round trip. */
export interface WorksheetDetail {
  worksheet: Worksheet;
  template: TestTemplate;
  computed: WorksheetComputed;
}

export interface CreateWorksheetRequest {
  template_id: number;
}

export interface WorksheetValuesRequest {
  /** `undefined`/`null` leaves stored values alone; `{}` clears them. */
  context_values?: Record<string, unknown> | null;
  group_values?: Record<string, WorksheetRow[]> | null;
}

export interface SaveWorksheetRequest extends WorksheetValuesRequest {
  /** Required by the backend when the parent TRF is `PendingADGLRelease`. */
  reason?: string | null;
}

export interface ConfirmWorksheetResponse {
  worksheet: Worksheet;
  computed: WorksheetComputed;
  test_line_id: number;
  test_line_result?: string | null;
}
