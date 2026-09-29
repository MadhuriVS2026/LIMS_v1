# Requirements Document: TRF — Test Request Form Module

## Introduction

This module builds the TRF (Test Request Form) vertical slice at `rd-lab-instance`, migrating the
functional baseline of the standalone Mendix TRF portal (`TRF_USER_MANUAL_V2 1.pdf`) onto the
existing FastAPI/React stack. A TRF is a request/approval container in which one or more
analytical tests are raised against a product/batch, routed through a two-gate departmental
approval chain (Formulation, then Analytical), tested by an Analyst, and released with an
auto-generated Analytical Test Report (ATR).

This iteration is scoped per the confirmed decisions in `design.md`:
- The Mendix 5-role model (Admin, Initiator, FDGL, ADGL, Analyst) maps onto the existing 4-role
  model: Initiator = Admin/Analyst, FDGL = Supervisor, ADGL = QA, Analyst = Analyst. No new roles
  are introduced.
- TRF/AR numbering uses the existing sequential-prefixed convention (`TRF-YYYYMMDD-XXXX`,
  `AR-YYYYMMDD-XXXX`), not the real Group-prefixed scheme (no `Group` master exists yet).
- FDGL Approve, ADGL Accept, Analyst Submit Results, and ADGL Release are e-signed; Refer-Back,
  Reject, and Analyst Accept are role-gated but require a comment instead of a signature (except
  Analyst Accept, which requires neither).
- Team/analyst assignment is simplified to self-assign-by-accept.
- Test specifications and results are free text this iteration — no structured calculation engine
  or Specification-master auto-fill.
- No file attachment capability is introduced this iteration; `raw_data_reference` remains a
  free-text reference field.
- A `source`/`stability_pull_ref` field is reserved on the TRF header for a future Stability
  integration, but that integration is not wired this iteration.
- ATR is a browser-printable export, not a server-rendered PDF service.
- No new roles, services, workers, or datastores are introduced.

## Glossary

- **TRF (Test Request Form)**: the request/approval container for one or more analytical tests
  raised against a product/batch.
- **FDGL (Formulation Department Group Lead)**: the first approval gate for a TRF. Mapped to the
  Supervisor role.
- **ADGL (Analytical Department Group Lead)**: the second approval gate; accepts the TRF, assigns
  the AR number, and performs final result release. Mapped to the QA role.
- **AR Number**: the secondary reference number assigned to a TRF at ADGL Accept, appearing
  alongside the TRF number on the ATR.
- **Test Line**: one row on a TRF representing a single test (from the Test Master) with its own
  specification, raw data reference, result, and remark.
- **Refer Back**: a gate action that returns the TRF to the Initiator for correction, requiring a
  comment, without rejecting it outright.
- **ATR (Analytical Test Report)**: the system-generated report rendering a Released TRF's header,
  test results, and full approval signature history.

## Requirements

### Requirement 1: TRF Creation and Test Line Management

**User Story:** As an Initiator (Admin or Analyst), I want to create a TRF with product/batch
details and add one or more tests to it, so that I can request analytical testing exactly as I
do today on the Mendix portal.

#### Acceptance Criteria

1. WHEN a user with the Admin or Analyst role creates a TRF THEN the system SHALL capture:
   product, batch number, label claim, stage of sample, group/department (free text), quantity,
   storage condition, storage period, pack details, manufactured by, manufacturing date,
   expiry-or-retest date, and remark, and SHALL set status to `Draft` with a generated
   `trf_number` in the format `TRF-YYYYMMDD-XXXX`.
2. WHEN a user adds a test line to a TRF whose status is `Draft` or `ReferredBack` THEN the
   system SHALL capture the selected test (from the Test Master), an optional specification,
   an optional raw data reference, and an optional remark, and SHALL assign the line a sequential
   `line_no`.
3. WHEN a user removes a test line from a TRF whose status is `Draft` or `ReferredBack` THEN the
   system SHALL delete that line without affecting the TRF header or other lines.
4. IF a user attempts to add or remove a test line on a TRF whose status is not `Draft`,
   `ReferredBack`, or (for a Supervisor/Admin acting as FDGL) `PendingFDGLApproval` THEN the
   system SHALL reject the request with a validation error and SHALL NOT modify the test line
   list.
5. IF a user without the Admin or Analyst role attempts to create a TRF THEN the system SHALL
   reject the request with an authorization error.

### Requirement 2: TRF Submission

**User Story:** As an Initiator, I want to submit my completed TRF for approval, so that it
enters the review chain.

#### Acceptance Criteria

1. WHEN an Initiator submits a `Draft` or `ReferredBack` TRF that has at least one test line THEN
   the system SHALL transition its status to `PendingFDGLApproval` and SHALL record the
   submitting user and timestamp.
2. IF a user attempts to submit a TRF with zero test lines THEN the system SHALL reject the
   request with a validation error and SHALL leave the status unchanged.
3. IF a user attempts to submit a TRF whose status is not `Draft` or `ReferredBack` THEN the
   system SHALL reject the request and SHALL leave the status unchanged.

### Requirement 3: FDGL (Formulation) Approval Gate

**User Story:** As an FDGL (Supervisor), I want to approve, refer back, or reject a submitted
TRF, so that only appropriately reviewed requests proceed to the Analytical department.

#### Acceptance Criteria

1. WHEN a Supervisor (or Admin) approves a TRF whose status is `PendingFDGLApproval` with a
   correct e-signature password THEN the system SHALL transition its status to
   `PendingADGLAcceptance` and SHALL record the approving user and timestamp.
2. IF an FDGL approval is attempted with an incorrect e-signature password THEN the system SHALL
   reject the request with an authentication error and SHALL leave the status unchanged.
3. WHEN a Supervisor (or Admin) refers back or rejects a TRF whose status is
   `PendingFDGLApproval` with a non-blank comment THEN the system SHALL transition its status to
   `ReferredBack` or `Rejected` respectively, and SHALL record the comment, acting user, and
   timestamp.
4. IF a refer-back or reject action is submitted with a blank or whitespace-only comment THEN the
   system SHALL reject the request and SHALL leave the status unchanged.
5. IF any FDGL action is attempted on a TRF whose status is not `PendingFDGLApproval` THEN the
   system SHALL reject the request and SHALL leave the status unchanged.
6. IF a user without the Supervisor or Admin role attempts any FDGL action THEN the system SHALL
   reject the request with an authorization error.

### Requirement 4: ADGL (Analytical) Acceptance Gate

**User Story:** As an ADGL (QA), I want to accept, refer back, or reject a TRF approved by FDGL,
so that accepted requests are assigned a traceable AR number and routed for testing.

#### Acceptance Criteria

1. WHEN a QA user (or Admin) accepts a TRF whose status is `PendingADGLAcceptance` with a correct
   e-signature password THEN the system SHALL transition its status to
   `PendingAnalystAcceptance`, SHALL generate and assign a unique `ar_number` in the format
   `AR-YYYYMMDD-XXXX`, and SHALL record the accepting user and timestamp.
2. IF an ADGL acceptance is attempted with an incorrect e-signature password THEN the system
   SHALL reject the request with an authentication error and SHALL leave the status and
   `ar_number` unchanged.
3. WHEN a QA user (or Admin) refers back or rejects a TRF whose status is
   `PendingADGLAcceptance` with a non-blank comment THEN the system SHALL transition its status
   to `ReferredBack` or `Rejected` respectively.
4. IF any ADGL acceptance-gate action is attempted on a TRF whose status is not
   `PendingADGLAcceptance` THEN the system SHALL reject the request and SHALL leave the status
   unchanged.
5. IF a user without the QA or Admin role attempts any ADGL acceptance-gate action THEN the
   system SHALL reject the request with an authorization error.
6. THE system SHALL assign `ar_number` exactly once per TRF, at the moment of ADGL acceptance,
   and SHALL NOT regenerate or reassign it on any subsequent transition.

### Requirement 5: Analyst Acceptance and Result Entry

**User Story:** As an Analyst, I want to accept an ADGL-accepted TRF and enter results for each
test line, so that I can perform and record the requested testing.

#### Acceptance Criteria

1. WHEN an Analyst (or Admin) accepts a TRF whose status is `PendingAnalystAcceptance` THEN the
   system SHALL transition its status to `InProgress` and SHALL record the accepting user and
   timestamp.
2. WHEN an Analyst refers back or rejects a TRF whose status is `PendingAnalystAcceptance` with a
   non-blank comment THEN the system SHALL transition its status to `ReferredBack` or `Rejected`
   respectively.
3. WHILE a TRF's status is `InProgress`, an Analyst (or Admin) SHALL be able to set or update the
   `result` and `remark` on any of its test lines.
4. WHEN an Analyst submits results for a TRF whose status is `InProgress` with a correct
   e-signature password THEN the system SHALL verify every test line has a non-blank `result`,
   and, if so, SHALL transition the TRF's status to `PendingADGLRelease` and record the
   submitting user and timestamp.
5. IF results submission is attempted while any test line has a blank `result` THEN the system
   SHALL reject the request with a validation error naming the incomplete line(s) and SHALL
   leave the status as `InProgress`.
6. IF results submission is attempted with an incorrect e-signature password THEN the system
   SHALL reject the request with an authentication error and SHALL leave the status unchanged.
7. IF a user without the Analyst or Admin role attempts any action in this requirement THEN the
   system SHALL reject the request with an authorization error.

### Requirement 6: ADGL Result Review, Correction, and Release

**User Story:** As an ADGL (QA), I want to review submitted results, correct them if needed, and
release the TRF, so that the results become visible to all stakeholders with full traceability.

#### Acceptance Criteria

1. WHILE a TRF's status is `PendingADGLRelease`, a QA user (or Admin) SHALL be able to correct
   the `result` or `remark` on any of its test lines.
2. IF a result correction is attempted on a TRF whose status is not `PendingADGLRelease`, or by a
   user without the QA or Admin role, THEN the system SHALL reject the request and SHALL leave
   the test line unchanged.
3. WHEN a QA user (or Admin) releases a TRF whose status is `PendingADGLRelease` with a correct
   e-signature password THEN the system SHALL transition its status to `Released`, SHALL record
   the releasing user and timestamp, and SHALL capture an immutable ATR snapshot of the TRF's
   header, test lines, and full approval signature history at that moment.
4. IF release is attempted with an incorrect e-signature password THEN the system SHALL reject
   the request with an authentication error and SHALL leave the status unchanged.
5. IF release is attempted on a TRF whose status is not `PendingADGLRelease` THEN the system
   SHALL reject the request and SHALL leave the status unchanged.

### Requirement 7: Refer-Back Resubmission

**User Story:** As an Initiator, I want to correct and resubmit a TRF that was referred back by
any gate, so that I don't have to create a new TRF from scratch.

#### Acceptance Criteria

1. WHILE a TRF's status is `ReferredBack`, the Initiator (or Admin) SHALL be able to add or
   remove test lines and edit header fields.
2. WHEN the Initiator (or Admin) resubmits a `ReferredBack` TRF THEN the system SHALL transition
   its status to `PendingFDGLApproval`, regardless of which gate (FDGL, ADGL, or Analyst)
   originally referred it back.
3. THE system SHALL NOT allow a resubmitted TRF to skip directly to `PendingADGLAcceptance` or
   `PendingAnalystAcceptance`.

### Requirement 8: Analytical Test Report (ATR)

**User Story:** As any user, I want to view and print the ATR for a released TRF, so that I have
a formal, auditable record of the completed testing and its full approval chain.

#### Acceptance Criteria

1. WHEN any authenticated user requests the ATR for a TRF whose status is `Released` THEN the
   system SHALL return the immutable snapshot captured at release time, including the header
   fields, every test line's specification/result/remark, the TRF and AR numbers, and the full
   signature chain (Initiated/Approved/Accepted/Analysed/Released By, with role and timestamp).
2. IF the ATR is requested for a TRF whose status is not `Released` THEN the system SHALL reject
   the request with a validation error.
3. THE system SHALL render the ATR as a browser-printable page, allowing the user to save it as a
   PDF via the browser's native print function.
4. THE ATR content SHALL NOT change after release, even if the underlying Product or Test Master
   data is later modified.

### Requirement 9: Role-Based Access Control

**User Story:** As a system administrator, I want TRF actions restricted to appropriate roles
using the existing four-role model, so that no new roles or authentication mechanisms are
introduced.

#### Acceptance Criteria

1. WHEN a user attempts to create a TRF or manage its test lines while Draft/ReferredBack THEN
   the system SHALL permit this only for roles Admin or Analyst.
2. WHEN a user attempts any FDGL gate action (approve/refer-back/reject) THEN the system SHALL
   permit this only for roles Admin or Supervisor.
3. WHEN a user attempts any ADGL acceptance-gate or release-gate action THEN the system SHALL
   permit this only for roles Admin or QA.
4. WHEN a user attempts to accept a TRF as Analyst, enter/submit test results, or refer
   back/reject at the Analyst gate THEN the system SHALL permit this only for roles Admin or
   Analyst.
5. WHEN any authenticated user (Admin, Analyst, Supervisor, or QA) requests to view a TRF, its
   test lines, or its ATR (once Released) THEN the system SHALL permit read access.

### Requirement 10: Audit Trail and Traceability

**User Story:** As a QA reviewer, I want every TRF state change captured in an immutable audit
trail, so that the module meets the same traceability standard as the rest of the system.

#### Acceptance Criteria

1. WHEN a TRF is created, submitted, approved, accepted, referred back, rejected, resubmitted,
   or released THEN the system SHALL write a corresponding `AuditLog` entry capturing the actor,
   action, timestamp, and old/new status.
2. WHEN a test line's result is submitted or corrected THEN the system SHALL write a
   corresponding `AuditLog` entry.
3. THE system SHALL NOT provide any user-facing capability to edit or delete an `AuditLog` entry
   once written.

### Requirement 11: Identifier Generation

**User Story:** As any system user, I want every TRF and its assigned AR to have a unique,
human-readable identifier, so that records are easy to reference and never collide.

#### Acceptance Criteria

1. THE system SHALL generate a unique `trf_number` for every `TestRequestForm` in the format
   `TRF-YYYYMMDD-XXXX`, following the existing sequential-prefixed generation convention.
2. THE system SHALL generate a unique `ar_number` in the format `AR-YYYYMMDD-XXXX` for every TRF
   at the moment of ADGL acceptance, following an analogous convention.

### Requirement 12: Frontend — TRF List and Detail

**User Story:** As any TRF stakeholder, I want a TRF list with status filtering and a detail page
showing the right actions for my role and the TRF's current state, so that the workflow is
discoverable and consistent with the rest of the application's UI patterns.

#### Acceptance Criteria

1. WHEN a user navigates to the TRF section THEN the system SHALL present a list of TRFs with a
   status filter, defaulting to a role-appropriate view (Initiator: own TRFs; FDGL: pending their
   approval; ADGL: pending their acceptance/release; Analyst: pending their acceptance).
2. WHEN a user opens a TRF THEN the system SHALL present its header fields, its test lines, and
   only the gate actions applicable to the TRF's current status and the viewer's role.
3. WHEN a gate action requires e-signature THEN the system SHALL present the existing
   `ESignDialog` component; WHEN a gate action requires only a comment THEN the system SHALL
   present a comment entry dialog.
4. WHEN a user opens a `Released` TRF THEN the system SHALL present a link to view/print its ATR.

## Out of Scope (this iteration)

- Structured per-test-type result templates and calculation engine (dissolution matrices, assay
  formulas, impurity tables) — test lines remain free-text `specification`/`result` this
  iteration.
- File attachment upload/storage for chromatograms or raw data sheets — `raw_data_reference`
  remains a free-text reference field.
- Empower (chromatography data system) integration.
- Automatic TRF generation from Stability protocol pull points — the `source`/
  `stability_pull_ref` fields are reserved but unwired this iteration.
- Group-prefixed TRF/AR numbering (`{GROUP}/TRF/{YY}/{NNNNN}`) — simplified sequential-prefixed
  numbering is used instead.
- Explicit ADGL-to-named-analyst or ADGL-to-team assignment — simplified to self-assign-by-accept.
- Specification-master auto-fill of per-test specifications.
- Compiled COA generation across multiple TRFs/batches (a separate future module per the roadmap).
- Notification delivery (email/in-portal) for pending approvals or referred-back TRFs.
- New roles distinct from the existing four (Admin, Analyst, Supervisor, QA).

## Dependencies and Assumptions Requiring Confirmation

- **Role mapping**: Initiator=Admin/Analyst, FDGL=Supervisor, ADGL=QA is a reasonable default but
  unconfirmed with the actual R&D organizational structure.
- **Numbering scheme**: sequential-prefixed `TRF-YYYYMMDD-XXXX`/`AR-YYYYMMDD-XXXX` deviates from
  the real `{GROUP}/TRF/{YY}/{NNNNN}` convention; revisit if Group-prefixed numbering is a hard
  regulatory requirement.
- **Team assignment**: self-assign-by-accept for Analysts is a simplification; confirm whether
  ADGL explicitly assigning a TRF to a named analyst/team is a hard requirement.
