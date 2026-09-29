# Requirements Document: MRN — Material Requisition & Consumption Module

## Introduction

This module digitizes the "last mile" of R&D plant material handling: from a material lot
completing GRN (Goods Receipt Note) in SAP, through a lab/project user raising a Material
Requisition Note (MRN) against one or more such lots, to the outbound consumption posting back
to SAP that deducts the requisitioned quantity against an internal order.

This iteration is scoped per the confirmed decisions in `design.md`:
- SAP dependency is narrowed to exactly two calls: an outbound **pull** of GRN-complete materials,
  and an outbound **post** of consumption per line item — no PO/vendor/cost-center master sync.
- An approval gate (Supervisor role, e-signed) sits between MRN submission and SAP posting.
- Project Code is captured as free text this iteration; Project Master validation is Phase 2.
- No new roles are introduced; the existing four (Admin, Analyst, Supervisor, QA) are reused,
  with Supervisor acting as the Store-Manager-equivalent approver.
- Email/in-portal notifications are deferred to Phase 2; audit trail entries are the traceability
  mechanism for this iteration.
- The GRN line natural key `(grn_document_no, grn_item_no)` and posting idempotency key are
  best-guess field names pending confirmation with SAP CoE, and must be treated as configurable/
  easily-revisable rather than hardcoded assumptions.

Built as a new vertical slice inside the existing `backend-v2` (FastAPI Clean Architecture) and
`frontend-react` codebases at `rd-lab-instance`, reusing the SAP CPI integration, audit/e-signature,
and RBAC patterns already established.

## Glossary

- **MRN**: Material Requisition Note — the record a lab/project user raises to request/consume
  quantity from one or more GRN-complete material lots.
- **GRN**: Goods Receipt Note — SAP's record that a material has been physically received.
- **Material Lot**: a specific batch of a material, at a specific plant, that has completed GRN
  in SAP and has a remaining quantity available for requisition.
- **Line Item**: one row on an MRN, requesting a specific quantity from a specific Material Lot.
- **Consumption Posting**: the outbound SAP call that deducts a line item's quantity against an
  internal order, and the record of that call's outcome.
- **Approve & Post**: the single Supervisor action, gated by e-signature, that approves a
  Submitted MRN and triggers consumption postings for all its line items.

## Requirements

### Requirement 1: GRN-Complete Material Queue (Inbound, Pull-Based)

**User Story:** As an Analyst, I want to see a queue of material lots that have completed GRN at
the R&D plant, so that I can select the correct lot(s) when raising a Material Requisition.

#### Acceptance Criteria

1. WHEN an Admin, Analyst, Supervisor, or QA user requests the Material Queue THEN the system
   SHALL return all `MRNMaterialLot` records with `available_quantity > 0`, ordered most-recently
   pulled first.
2. WHEN a user with role Admin, Analyst, or Supervisor triggers a manual pull from SAP THEN the
   system SHALL call `ISAPClient.read_grn_completed_materials(plant)` and upsert the returned
   lots into `MRNMaterialLot`, keyed by `(grn_document_no, grn_item_no)`.
3. WHEN a pulled GRN line matches an existing `MRNMaterialLot` by its natural key THEN the system
   SHALL update that lot's fields (quantity, batch, dates) rather than creating a duplicate row.
4. WHEN a pull from SAP completes (success or failure) THEN the system SHALL write one
   `SAPIntegrationLog` entry (direction OUTBOUND) and one `AuditLog` entry recording the actor,
   the count of lots pulled, and any error.
5. IF the SAP pull call fails THEN the system SHALL surface the error to the requesting user via
   the API response AND SHALL NOT modify any existing `MRNMaterialLot` records.
6. WHEN a Material Lot's `available_quantity` (computed as `original_quantity - consumed_quantity`)
   reaches zero THEN the system SHALL exclude it from the default Material Queue view but SHALL
   retain it as queryable by its historical record.
7. THE `SimulatedSAPClient` implementation of `read_grn_completed_materials` SHALL return
   realistic mock lot data so the module is fully functional end-to-end without live SAP
   credentials, matching the existing simulated-client pattern for other SAP calls.

### Requirement 2: Raising a Material Requisition (MRN)

**User Story:** As an Analyst, I want to create an MRN and add one or more line items against
material lots in the queue, so that I can request specific quantities for my testing/project work.

#### Acceptance Criteria

1. WHEN an Analyst or Admin creates a new MRN THEN the system SHALL create a `MaterialRequisition`
   header record with status `Draft`, an auto-generated MRN number, the creating user, and a
   timestamp.
2. WHEN a user adds a line item to a Draft MRN THEN the system SHALL require selection of an
   existing `MRNMaterialLot`, a requested quantity, and a project code (free text), and SHALL
   validate that the requested quantity does not exceed the lot's current `available_quantity`.
3. IF a user attempts to add a line item requesting more than the lot's `available_quantity`
   THEN the system SHALL reject the request with a validation error identifying the maximum
   allowable quantity.
4. WHEN a user removes a line item from a Draft MRN THEN the system SHALL delete that line item
   without affecting the header or other line items.
5. WHEN a user submits an MRN THEN the system SHALL transition its status from `Draft` to
   `Submitted`, SHALL lock all line items against further add/remove/edit, and SHALL record the
   submitting user and timestamp.
6. IF a user attempts to submit an MRN with zero line items THEN the system SHALL reject the
   submission with a validation error.
7. WHEN an MRN is in `Draft` status THEN only its creating user or an Admin SHALL be permitted to
   edit or submit it.
8. THE system SHALL generate MRN numbers using a dedicated `MRNNumberGenerator` domain service,
   sibling to the existing `SampleCodeGenerator`, producing a unique, sequential, human-readable
   identifier per MRN.

### Requirement 3: Approval and SAP Consumption Posting

**User Story:** As a Supervisor, I want to review a Submitted MRN and, upon approval with my
e-signature, trigger consumption posting to SAP for every line item, so that material deduction
is authorized, auditable, and reflected in SAP as an internal order consumption.

#### Acceptance Criteria

1. WHEN a Supervisor views a Submitted MRN THEN the system SHALL display all line items with
   their requested quantities, source lots, and project codes for review.
2. WHEN a Supervisor initiates "Approve & Post" on a Submitted MRN THEN the system SHALL require
   e-signature re-authentication (password re-entry) before proceeding, consistent with the
   existing `verify_esignature` pattern used for Usage Decision posting and batch release.
3. WHEN e-signature verification succeeds THEN the system SHALL transition the MRN to
   `PostingInProgress` and SHALL attempt, for each line item independently, a call to
   `ISAPClient.post_material_consumption` with an idempotency key derived from the MRN number and
   line number.
4. IF a line item's consumption posting succeeds THEN the system SHALL record the returned SAP
   document number on the `ConsumptionPosting` record, set the line item status to
   `ConsumptionPosted`, and increment the source `MRNMaterialLot.consumed_quantity` by the posted
   quantity.
5. IF a line item's consumption posting fails THEN the system SHALL record the error message on
   the `ConsumptionPosting` record and set the line item status to `PostingFailed`, WITHOUT
   affecting any other line item's posting attempt.
6. WHEN all line items on an MRN have been attempted THEN the system SHALL set the MRN header
   status to `Posted` if all succeeded, `PartiallyPosted` if some succeeded and some failed, or
   `PostingFailed` if all failed.
7. WHEN a Supervisor retries posting for an MRN in `PartiallyPosted` or `PostingFailed` status
   THEN the system SHALL only re-attempt line items with status `PostingFailed`, using the same
   idempotency key as the original attempt for each such line item.
8. WHEN any consumption posting attempt (success or failure) occurs THEN the system SHALL write
   one `SAPIntegrationLog` entry (direction OUTBOUND) and one `AuditLog` entry per line item,
   capturing the actor, material lot, quantity, and outcome.
9. IF a user without the Supervisor or Admin role attempts to approve-and-post an MRN THEN the
   system SHALL reject the request with an authorization error.
10. THE `SimulatedSAPClient` implementation of `post_material_consumption` SHALL return a
    realistic mock SAP document number so the module is fully functional end-to-end without live
    SAP credentials.

### Requirement 4: Material Lot Lifecycle Derivation

**User Story:** As any system user, I want a Material Lot's status to always accurately reflect
how much of it has been consumed, so that the Material Queue never shows stale or incorrect
availability.

#### Acceptance Criteria

1. THE system SHALL derive `MRNMaterialLot.status` from its quantities rather than storing it as
   an independently-settable field: `Available` when `consumed_quantity == 0`,
   `PartiallyConsumed` when `0 < consumed_quantity < original_quantity`, and `Exhausted` when
   `consumed_quantity == original_quantity`.
2. WHEN a consumption posting succeeds for any line item against a lot THEN the system SHALL
   recompute that lot's derived status immediately within the same transaction.
3. IF a lot's `available_quantity` is zero THEN the system SHALL prevent any new MRN line item
   from being added against it, even if the lot is still visible in historical views.

### Requirement 5: Audit Trail and Traceability

**User Story:** As a QA reviewer, I want every MRN state change and every SAP interaction to be
captured in an immutable audit trail, so that the module meets 21 CFR Part 11 traceability
requirements consistent with the rest of the system.

#### Acceptance Criteria

1. WHEN an MRN is created, has a line item added or removed, is submitted, is approved-and-posted,
   or has any line item's posting retried THEN the system SHALL write a corresponding `AuditLog`
   entry capturing the actor, action, timestamp, and relevant old/new values.
2. WHEN a Material Lot pull from SAP occurs THEN the system SHALL write a corresponding
   `AuditLog` entry independent of the `SAPIntegrationLog` entry.
3. THE audit trail entries produced by this module SHALL use the same `AuditLog` and
   `SAPIntegrationLog` entities and repositories already used by the Sample Manager and SAP
   Integration modules, with no schema divergence.
4. THE system SHALL NOT provide any user-facing capability to edit or delete an `AuditLog` or
   `SAPIntegrationLog` entry once written.

### Requirement 6: Role-Based Access Control

**User Story:** As a system administrator, I want MRN actions restricted to appropriate roles
using the existing four-role model, so that segregation of duties (requester ≠ approver) is
enforced without introducing new roles or authentication mechanisms.

#### Acceptance Criteria

1. WHEN a user attempts to create an MRN, add/remove a line item, or submit an MRN THEN the
   system SHALL permit this only for roles Admin or Analyst.
2. WHEN a user attempts to approve-and-post or retry a failed posting on an MRN THEN the system
   SHALL permit this only for roles Admin or Supervisor.
3. WHEN a user attempts to trigger a manual SAP material queue pull THEN the system SHALL permit
   this only for roles Admin, Analyst, or Supervisor.
4. WHEN any authenticated user (Admin, Analyst, Supervisor, or QA) requests to view the Material
   Queue, an MRN, or its line items THEN the system SHALL permit read access regardless of who
   created the MRN.
5. IF the user who submitted an MRN attempts to also approve-and-post that same MRN THEN the
   system SHALL NOT block this at the role-permission layer (since Supervisor and Analyst are
   distinct roles held by different accounts in practice), but the design SHALL document this as
   a segregation-of-duties assumption reliant on organizational role assignment rather than a
   system-enforced same-user check.

### Requirement 7: Frontend — Material Queue and MRN Workspace

**User Story:** As an Analyst or Supervisor, I want dedicated screens to view the material queue,
raise/manage MRNs, and approve-and-post them, consistent with the existing application's UI
patterns.

#### Acceptance Criteria

1. WHEN a user navigates to the Material Queue page THEN the system SHALL display all available
   material lots in a data table with columns for material, batch, plant, available quantity,
   and GRN reference, consistent with the existing `DataTable`/`Column` patterns used elsewhere
   in the app.
2. WHEN a user with role Admin, Analyst, or Supervisor clicks "Pull from SAP" on the Material
   Queue page THEN the system SHALL call the pull endpoint and refresh the displayed queue,
   showing a toast notification of the outcome using the existing `toastService`.
3. WHEN a user views "My MRNs" THEN the system SHALL display MRNs they created (or, for
   Admin/Supervisor, all MRNs) with their current status using the existing `StatusBadge`
   component.
4. WHEN a user opens an MRN in `Draft` status THEN the system SHALL present a line-item editor
   allowing add/remove of line items against queued material lots.
5. WHEN a Supervisor opens an MRN in `Submitted`, `PartiallyPosted`, or `PostingFailed` status
   THEN the system SHALL present an "Approve & Post" (or "Retry Failed Lines") action gated by
   the existing `ESignDialog` component.
6. WHEN consumption posting results are available for an MRN THEN the system SHALL display each
   line item's individual status (Requisitioned / ConsumptionPosted / PostingFailed) and, where
   applicable, the SAP document number or error message.

## Out of Scope (this iteration)

- Purchase Order or vendor master synchronization.
- Store Executive physical receipt verification / discrepancy holding (`VERIFIED ⇄ HELD`).
- Project Code → Cost Center master validation (Project Master sync).
- Email or in-portal notifications (BRD Appendix B).
- New roles (Store Executive, Store Manager, Department Head) distinct from the existing four.
- Reservation of material lots ahead of requisition.
- Excel/PDF export of MRN or consumption reports.

## Dependencies and Assumptions Requiring Confirmation

- The exact SAP CPI payload field names for GRN-complete materials and the consumption posting
  request/response contract are unconfirmed; `(grn_document_no, grn_item_no)` is a best-guess
  natural key pending SAP CoE sign-off, and the implementation must isolate this mapping so it is
  easily revised without touching domain/application logic.
- The R&D plant code used to filter the GRN-complete material pull is not yet known and must be
  supplied via configuration, not hardcoded.
