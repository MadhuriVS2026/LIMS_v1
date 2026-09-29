# Requirements Document: Stability Management Module

## Introduction

This module completes the Stability Management vertical slice at `rd-lab-instance`. Today the
module supports only Draft protocol creation and flat, unscheduled time-point rows with no
approval workflow, no Loading Matrix, no linkage to the Sample Manager, and no report generation.

This iteration is scoped per the confirmed decisions in `design.md`:
- The Loading Matrix models both the real protocol document's day-based time points (15, 30, 60,
  90, 180, 270, 365, 545, 730, 1095 days, plus a Reserve column) and a derived month label,
  supporting condition × time-point scheduling exactly as the real "Stability Protocol Format"
  document depicts.
- The protocol approval workflow uses the existing Supervisor role for both "Checked By" steps
  (Formulation, then Analytical) as two sequential e-signed transitions; no new "Approver" role
  is introduced.
- Time-point pulls auto-create a Sample in the Sample Manager via the existing `SampleService`,
  reusing all existing result-entry/OOS/release logic rather than duplicating it.
- Stability Report generation is manually triggered but auto-assembles its data from completed
  time points; the report's four-signature footer collapses to two system-enforced e-signed
  gates (Prepared = Analyst, Approved = QA), with Checked/Reviewed captured as free-text fields.
- The module is extracted from Resource Manager into its own top-level "Stability Management"
  frontend section and its own backend service/repository/endpoints, mirroring how MRN was
  extracted into its own module.
- No new roles, services, workers, or datastores are introduced.

## Glossary

- **Stability Protocol**: the master record for a stability study (product, condition(s),
  duration, Loading Matrix, approval status).
- **Loading Matrix**: the condition × time-point grid defining which combinations of storage
  condition and elapsed time are scheduled for testing, per the real "Stability Protocol Format"
  document.
- **Matrix Cell**: one cell of the Loading Matrix — a specific condition + time point (in days),
  optionally checked/scheduled, with an optional note.
- **Time Point**: a scheduled pull-and-test event for a specific batch, at a specific condition
  and elapsed duration, tracked as a `StabilitySample`.
- **Pull**: the act of retrieving a stored batch sample for testing at its scheduled time point,
  which creates a linked Sample in the Sample Manager.
- **Stability Report**: the assembled results document for a protocol, following the real
  "Stability Report Format" document's structure, with its own sign-off workflow.
- **Formulation Check / Analytical Check**: the two sequential Supervisor-role e-signed review
  steps that move a protocol from Draft to Active, mirroring the real document's two "Checked By"
  signatures.

## Requirements

### Requirement 1: Loading Matrix Modeling and Editing

**User Story:** As a Supervisor or Analyst, I want to define which storage conditions and time
points apply to a stability protocol using a matrix layout matching the real protocol form, so
that the schedule reflects exactly what will be tested.

#### Acceptance Criteria

1. WHEN a user views a Draft protocol's Loading Matrix THEN the system SHALL present a grid of
   condition rows × time-point columns (in days: 15, 30, 60, 90, 180, 270, 365, 545, 730, 1095)
   plus a Reserve column, matching the structure of the real Stability Protocol Format document.
2. WHEN a user checks/unchecks a matrix cell THEN the system SHALL persist that cell's
   `is_scheduled` flag, and MAY persist a free-text note per cell (e.g. "17 vials FP").
3. WHEN a user saves Loading Matrix changes for a protocol whose status is `Draft` THEN the
   system SHALL upsert `StabilityMatrixCell` rows keyed by `(protocol_id, condition,
   time_point_days, is_reserve)`, updating existing cells rather than creating duplicates.
4. IF a user attempts to add, update, or remove Loading Matrix cells on a protocol whose status
   is not `Draft` THEN the system SHALL reject the request with a validation error and SHALL NOT
   modify the matrix.
5. THE system SHALL derive and store a human-readable month label (e.g. "3M") for each
   day-based time point for display and reporting purposes, alongside the exact day value.
6. THE system SHALL allow `condition` to be entered as free text per matrix cell, offering the
   six condition values from the real document (40°C±2°C/75%±5%RH, 30°C±2°C/65%±5%RH,
   30°C±2°C/75%±5%RH, 25°C±2°C/60%±5%RH, 5°C±3°C, Other) as suggested defaults.

### Requirement 2: Protocol Header Fields

**User Story:** As a Supervisor, I want to capture all the header information from the real
Stability Protocol Format document, so that the system-generated protocol matches what is
currently prepared manually.

#### Acceptance Criteria

1. WHEN a user creates or edits a Draft protocol THEN the system SHALL capture: label claim,
   manufacturing date, batch number, placebo batch number, batch size, stability initiation date,
   number of samples/time points, fill volume, API name/batch/source, primary pack, secondary
   pack, headspace, orientation (Upright/Inverted), and remarks — in addition to the existing
   product, condition, duration, and study type fields.
2. THE system SHALL retain `duration_months` and `testing_frequency` as coarse summary fields on
   the protocol header, distinct from and not authoritative over the Loading Matrix's
   `time_point_days` values.

### Requirement 3: Two-Step Protocol Approval Workflow

**User Story:** As a Supervisor, I want to perform the Formulation and Analytical checks on a
protocol with e-signature, so that the system enforces the same two-signature review the paper
process requires before a protocol becomes usable.

#### Acceptance Criteria

1. WHEN a Supervisor (or Admin) performs "Formulation Check" on a `Draft` protocol with a correct
   e-signature password THEN the system SHALL transition the protocol's status to
   `FormulationChecked` and SHALL record the acting user and timestamp as
   `formulation_checked_by`/`formulation_checked_at`.
2. IF a Formulation Check is attempted with an incorrect e-signature password THEN the system
   SHALL reject the request with an authentication error and SHALL leave the protocol's status
   unchanged.
3. IF a Formulation Check is attempted on a protocol whose status is not `Draft` THEN the system
   SHALL reject the request and SHALL leave the protocol's status unchanged.
4. WHEN a Supervisor (or Admin) performs "Analytical Check" on a `FormulationChecked` protocol
   with a correct e-signature password THEN the system SHALL transition the protocol's status to
   `Active` and SHALL record the acting user and timestamp as `approved_by`/`approved_at`.
5. IF an Analytical Check is attempted on a protocol whose status is not `FormulationChecked`
   (including `Draft`, `Active`, `Completed`, or `Cancelled`) THEN the system SHALL reject the
   request and SHALL leave the protocol's status unchanged.
6. IF an Analytical Check is attempted with an incorrect e-signature password THEN the system
   SHALL reject the request with an authentication error and SHALL leave the protocol's status
   unchanged.
7. IF a user without the Supervisor or Admin role attempts either check THEN the system SHALL
   reject the request with an authorization error.

### Requirement 4: Time-Point Schedule Generation

**User Story:** As an Analyst or Supervisor, I want to generate the full time-point pull schedule
for an Active protocol's batches, so that I don't have to manually create each scheduled sample
row.

#### Acceptance Criteria

1. WHEN a user triggers "Generate Schedule" for an `Active` protocol with one or more batch
   numbers THEN the system SHALL create exactly one `StabilitySample` record per
   `(batch_number, matrix_cell)` combination, for every `StabilityMatrixCell` where
   `is_scheduled == true` and `is_reserve == false`.
2. IF "Generate Schedule" is attempted on a protocol whose status is not `Active` THEN the system
   SHALL reject the request and SHALL NOT create any `StabilitySample` records.
3. WHEN a `StabilitySample` is generated THEN the system SHALL compute its `scheduled_date` as
   the protocol's `stability_initiation_date` plus the matrix cell's `time_point_days`.
4. THE system SHALL NOT create `StabilitySample` records for matrix cells marked `is_reserve` or
   left unchecked (`is_scheduled == false`).
5. IF "Generate Schedule" is triggered again for a protocol/batch combination that already has
   generated `StabilitySample` records for the same matrix cells THEN the system SHALL NOT create
   duplicate rows.

### Requirement 5: Time-Point Pull and Sample Manager Linkage

**User Story:** As an Analyst, I want pulling a scheduled time point to automatically create the
corresponding Sample for testing, so that I don't have to re-enter the same information in two
places.

#### Acceptance Criteria

1. WHEN an Analyst (or Admin) pulls a `StabilitySample` whose derived status is `Scheduled` THEN
   the system SHALL call the existing Sample Manager's sample-logging capability using the
   protocol's product and the time point's batch number, SHALL link the resulting Sample's
   identifier back onto the `StabilitySample`, and SHALL record the pull date.
2. IF a pull is attempted on a `StabilitySample` whose derived status is not `Scheduled` THEN the
   system SHALL reject the request and SHALL leave the `StabilitySample` unchanged.
3. IF Sample creation fails during a pull THEN the system SHALL NOT leave the `StabilitySample`
   with a partially-updated state (e.g. a `pull_date` set without a linked sample, or vice versa).
4. THE system SHALL derive `StabilitySample.status` from the linked Sample's current status on
   every read, rather than storing it as an independently-settable field once a Sample is linked:
   `Scheduled` when no Sample is linked, `Pulled` when the linked Sample's status is `Logged` or
   `Received`, `Testing` while the linked Sample has results in progress, and `Completed` when
   the linked Sample's status is `Approved` or `Rejected`.
5. THE system SHALL NOT duplicate any result-entry, OOS-detection, or release logic already
   implemented in the Sample Manager; all testing and result workflow for a pulled time point
   continues through the existing Sample Manager UI/API against the linked Sample.

### Requirement 6: Stability Report Generation

**User Story:** As an Analyst, I want to generate a Stability Report for a protocol that
assembles all completed time-point results into the format used today, so that I don't have to
manually transcribe results from the Sample Manager.

#### Acceptance Criteria

1. WHEN a user triggers "Generate Report" for a protocol THEN the system SHALL assemble a results
   table containing, for each test, its specification and its result at each time point whose
   `StabilitySample` derived status is `Completed`, and SHALL exclude time points that are
   `Scheduled`, `Pulled`, or `Testing`.
2. WHEN "Generate Report" is triggered for a protocol with no existing `Prepared` or `Approved`
   `StabilityReport` THEN the system SHALL create or overwrite a `Draft` `StabilityReport` with
   the newly assembled data.
3. IF "Generate Report" is triggered for a protocol that already has a `Prepared` or `Approved`
   `StabilityReport` THEN the system SHALL create a new `Draft` report record rather than
   modifying the existing signed report, which SHALL remain unchanged.
4. THE system SHALL populate the generated report's header fields (product name,
   composition/label, manufactured at, study type, batch no., condition, batch size, date of
   commencement, manufacturing date, protocol no., expiry date, API source/batch, packing) from
   the source protocol at generation time.

### Requirement 7: Stability Report Sign-Off

**User Story:** As an Analyst and QA reviewer, I want to formally prepare and approve a Stability
Report with e-signature, so that the report is traceable and matches the real document's
sign-off intent.

#### Acceptance Criteria

1. WHEN an Analyst (or Admin) performs "Prepare" on a `Draft` report with a correct e-signature
   password THEN the system SHALL transition the report's status to `Prepared` and SHALL record
   the acting user and timestamp as `prepared_by`/`prepared_at`.
2. IF "Prepare" is attempted on a report whose status is not `Draft`, or with an incorrect
   e-signature password, THEN the system SHALL reject the request and SHALL leave the report's
   status unchanged.
3. WHEN a QA user (or Admin) performs "Approve" on a `Prepared` report with a correct e-signature
   password THEN the system SHALL transition the report's status to `Approved` and SHALL record
   the acting user and timestamp as `approved_by`/`approved_at`.
4. IF "Approve" is attempted on a report whose status is not `Prepared`, or with an incorrect
   e-signature password, THEN the system SHALL reject the request and SHALL leave the report's
   status unchanged.
5. IF a user without the Analyst or Admin role attempts "Prepare", or a user without the QA or
   Admin role attempts "Approve", THEN the system SHALL reject the request with an authorization
   error.
6. THE system SHALL capture `checked_by_name` and `reviewed_by_name` as free-text fields on the
   report for print fidelity to the real document, without gating any workflow transition on
   them.

### Requirement 8: Role-Based Access Control

**User Story:** As a system administrator, I want Stability actions restricted to appropriate
roles using the existing four-role model, so that no new roles or authentication mechanisms are
introduced.

#### Acceptance Criteria

1. WHEN a user attempts to create a protocol, edit its header, or edit its Loading Matrix THEN
   the system SHALL permit this only for roles Admin or Supervisor.
2. WHEN a user attempts a Formulation Check or Analytical Check THEN the system SHALL permit this
   only for roles Admin or Supervisor.
3. WHEN a user attempts to generate a time-point schedule or pull a time point THEN the system
   SHALL permit this only for roles Admin or Analyst.
4. WHEN a user attempts to generate a Stability Report or "Prepare" it THEN the system SHALL
   permit this only for roles Admin or Analyst.
5. WHEN a user attempts to "Approve" a Stability Report THEN the system SHALL permit this only
   for roles Admin or QA.
6. WHEN any authenticated user (Admin, Analyst, Supervisor, or QA) requests to view a protocol,
   its Loading Matrix, its time points, or its reports THEN the system SHALL permit read access.

### Requirement 9: Audit Trail and Traceability

**User Story:** As a QA reviewer, I want every Stability state change captured in an immutable
audit trail, so that the module meets the same traceability standard as the rest of the system.

#### Acceptance Criteria

1. WHEN a `StabilityProtocol` is created, has its Loading Matrix edited, or undergoes a
   Formulation Check, Analytical Check, or status change THEN the system SHALL write a
   corresponding `AuditLog` entry capturing the actor, action, timestamp, and old/new status.
2. WHEN a `StabilitySample` is generated or pulled THEN the system SHALL write a corresponding
   `AuditLog` entry.
3. WHEN a `StabilityReport` is generated, prepared, or approved THEN the system SHALL write a
   corresponding `AuditLog` entry.
4. THE system SHALL NOT provide any user-facing capability to edit or delete an `AuditLog` entry
   once written.

### Requirement 10: Identifier Generation

**User Story:** As any system user, I want every protocol and report to have a unique,
human-readable identifier, so that records are easy to reference and never collide.

#### Acceptance Criteria

1. THE system SHALL generate a unique `protocol_code` for every `StabilityProtocol`, following
   the existing generation convention (sequential, prefixed).
2. THE system SHALL generate a unique `report_number` for every `StabilityReport`, following an
   analogous sequential, prefixed convention.

### Requirement 11: Frontend — Stability Management Section

**User Story:** As an Analyst, Supervisor, or QA user, I want a dedicated Stability Management
section with pages for protocols, the Loading Matrix, schedule/pull, and reports, so that the
workflow is discoverable and consistent with the rest of the application's UI patterns.

#### Acceptance Criteria

1. WHEN a user navigates to the application THEN the system SHALL present "Stability Management"
   as its own top-level nav section (not nested under Resource Manager), replacing the existing
   flat Stability page.
2. WHEN a user opens a protocol in `Draft` status THEN the system SHALL present a Loading Matrix
   builder (grid of condition × time-point checkboxes with per-cell notes) and the two-step check
   actions, gated by the existing `ESignDialog` component.
3. WHEN a user opens an `Active` protocol THEN the system SHALL present a schedule/pull workspace
   showing all `StabilitySample` rows with their derived status, and a "Pull" action for rows in
   `Scheduled` status.
4. WHEN a user opens a protocol's Reports tab THEN the system SHALL present "Generate Report" and,
   for existing reports, "Prepare"/"Approve" actions gated by `ESignDialog`, with each line item's
   or report's status shown via the existing `StatusBadge` component.

## Out of Scope (this iteration)

- Excel/PDF export or print-formatted rendering of the Loading Matrix, Protocol, or Report
  documents (data is captured and structured to support this later, but rendering is deferred).
- Automatic protocol status transition to `Completed` when all time points finish (left as a
  manual action this iteration).
- Storage/inventory tracking of physical stability chamber capacity or reserve sample counts.
- Notification delivery (email/in-portal) for due time points.
- New roles distinct from the existing four (Admin, Analyst, Supervisor, QA).

## Dependencies and Assumptions Requiring Confirmation

- **Batch selection at schedule-generation time**: `generate_schedule()` accepts an explicit list
  of batch numbers (defaulting to the protocol's primary batch) rather than assuming only one
  batch is ever scheduled. Confirm whether the Placebo Batch also receives its own time-point
  pulls or is tracked only administratively.
- **Standard day list customizability**: the default day list (15/30/60/90/180/270/365/545/730/
  1095 + Reserve) is taken directly from the real Stability Protocol Format document. Confirm
  whether protocols ever need non-standard day values, or whether this should be a fixed,
  non-editable set of columns.
- **Condition list**: the six condition values from the real document are offered as suggested
  defaults but `condition` remains free text, consistent with the existing entity's design.
