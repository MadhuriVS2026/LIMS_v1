# Requirements Document

TRF Test Templates, Calculation Engine, Attachments & COA

## Introduction

This module replaces the R&D Analytical Development team's 35 standalone Excel calculation
workbooks (`rd-lab-instance/Test types/`) with configurable, schema-driven test templates inside
the LIMS, wires them into the existing TRF workflow, adds PDF attachment capability per TRF, and
extends COA generation to compile all tests and results.

Today an analyst opens the correct `.xlsx`/`.xls` sheet, types standard/sample preparation
weights and dilution volumes, pastes chromatographic peak **areas** exported from the Waters
chromatography data system (CDS), and Excel formulas compute the reportable result. There is no
audit trail, no version control on the formulas, no link to the TRF, and results are re-keyed by
hand into the TRF. This module brings that calculation work inside the system.

**Analysis basis:** all 35 workbooks were parsed (formulas included) and classified into 14
calculation archetypes. The full field/formula analysis is recorded in `design.md`; the raw
structural dumps are retained at `rd-lab-instance/_inspect_tests/` as implementation reference.

## Glossary

- **Test Template**: a versioned, configurable definition of one analytical calculation sheet —
  its context fields, analyst input fields, area inputs, calculated fields with formulas,
  repeating row groups, and acceptance criteria. Replaces one Excel workbook.
- **Archetype**: a family of test templates sharing the same calculation structure (e.g. "Assay
  by HPLC against external standard"). 14 archetypes cover all 35 workbooks.
- **Test Execution** (or *worksheet instance*): the filled-in instance of a Test Template attached
  to one TRF test line, holding the analyst's entered values, the areas, and the computed results.
- **Area / Response**: a chromatographic peak area, today typed in manually from the Waters CDS,
  later imported automatically. Marked with an explicit `source` so the import path can be added
  without changing any template.
- **Dilution chain**: the ordered sequence of `(aliquot, diluted-to)` volume steps that converts a
  weighed amount into a solution concentration. The single most common structure across all forms.
- **Bracketing standard (BKT)**: standard injections interspersed through a long analytical run.
  Their statistics are *pooled cumulatively* with the initial standard replicates, never computed
  standalone.
- **RRF (Relative Response Factor)**: per-impurity correction factor, applied either as a
  multiplier or a divisor depending on a template-level mode flag.
- **System suitability (SST)**: pre-conditions that must pass for a run to be valid (e.g. standard
  replicate %RSD NMT 2.0%).
- **COA (Certificate of Analysis)**: the compiled release document listing every test, its
  specification, and its reportable result for a batch.

## Requirements

### Requirement 1: Test Template Master

**User Story:** As an Analytical Development lead, I want to define and version test templates in
the masters, so that the lab's calculation sheets are controlled, reusable configuration rather
than loose Excel files.

#### Acceptance Criteria

1. WHEN a user with the Admin role creates a Test Template THEN the system SHALL capture a
   template code, name, the owning archetype, the target Test (from the Test Master), a result-unit
   selection, and a structured definition of its field groups, and SHALL set status to `Draft`
   with version 1.
2. THE system SHALL support template definitions expressing: context fields (auto-populated from
   TRF/product/batch/session), analyst input fields (numeric/text/date/select/picker), dilution
   chains, area inputs, response matrices with repeating rows and columns, calculated fields with
   formula expressions and explicit rounding, template-level configuration flags, and acceptance
   criteria.
3. WHEN a template is submitted for approval and approved with a valid e-signature by a Supervisor
   or QA user THEN the system SHALL transition it to `Active` and SHALL make it selectable on TRF
   test lines.
4. WHEN an `Active` template is edited THEN the system SHALL create a new `Draft` version rather
   than mutating the active version, and SHALL leave previously executed worksheets bound to the
   version they were executed against.
5. IF a user without the Admin role attempts to create or edit a Test Template THEN the system
   SHALL reject the request with an authorization error.
6. THE system SHALL be seeded with at least one working template per archetype implemented in this
   iteration, derived from the corresponding source workbook.

### Requirement 2: Calculation Engine

**User Story:** As an Analyst, I want the system to compute results from my entered values exactly
as the Excel sheets do today, so that I can trust the numbers without re-checking them in Excel.

#### Acceptance Criteria

1. WHEN a worksheet's inputs change THEN the system SHALL evaluate all dependent calculated fields
   in dependency order and SHALL return the computed values without persisting them until saved.
2. THE calculation engine SHALL support: arithmetic; `mean`, `sd`, `rsd`, `min`, `max`, `sum`,
   `count` over ranges and row groups; `round`, `trunc`, `sqrt`, `ln`, `exp`; `if`/`and`/`or`;
   `slope`, `intercept`, `correl`; blank-skipping aggregation; references to previous rows and
   running totals for sequential (dissolution) calculations; and cumulative pooling of a range with
   one or more additional ranges (bracketing standards).
3. THE engine SHALL apply rounding and truncation exactly where the source formula applies it,
   including intermediate steps, because rounding position is load-bearing for reported values.
4. WHERE a source formula sums already-rounded values THEN the engine SHALL sum the rounded values,
   not the raw values.
5. IF a formula's inputs are missing or produce a division by zero THEN the system SHALL return an
   empty result for that field rather than an error, matching the source sheets' `IFERROR(...,"")`
   behavior, and SHALL NOT block entry of other fields.
6. THE engine SHALL be deterministic and side-effect free: the same inputs SHALL always produce the
   same outputs.
7. WHEN a calculated result is persisted THEN the system SHALL store both the computed value and
   the template version and input snapshot used to produce it.

### Requirement 3: Dilution Chain and Master Equation

**User Story:** As an Analyst, I want dilution steps entered the way I record them on the bench, so
that entry matches my actual workflow.

#### Acceptance Criteria

1. THE system SHALL represent a dilution chain as an ordered list of steps, each with an aliquot
   volume and a diluted-to volume, and SHALL expose both the forward factor and the inverse factor
   for use in formulas.
2. WHERE a dilution step is unused THEN the system SHALL treat it as a neutral `1/1` step.
3. THE system SHALL compute standard concentration as the standard weight divided through its
   dilution chain, multiplied by the molecular-weight ratio (base/salt) and the potency term, scaled
   to the template's declared concentration unit.
4. WHERE molecular weight base or salt is recorded as not-applicable THEN the system SHALL omit the
   molecular-weight ratio from the calculation.
5. THE system SHALL compute a sample's reportable result as the sample response divided by the mean
   standard response, multiplied by the standard concentration terms, the inverse sample dilution
   chain, the sample amount normaliser, and the template's declared unit normaliser.

### Requirement 4: Area Entry (Waters CDS Interim)

**User Story:** As an Analyst, I want to enter peak areas manually now and have them imported from
Waters later, so that the switch to the integration does not require rebuilding my templates.

#### Acceptance Criteria

1. THE system SHALL present every area field as a manually editable numeric input.
2. THE system SHALL record a `source` on every area value, defaulting to `ManualEntry`.
3. THE system SHALL support area fields arranged as: single values, replicate series (standard
   injections), bracketing blocks, per-sample duplicate injections, per-impurity peak responses
   with retention times, and unit × timepoint matrices.
4. WHERE a template declares blank-correction THEN the system SHALL subtract the entered blank area
   from every standard and sample response before computing ratios, and SHALL report the blank
   interference percentage.
5. THE system SHALL define area ingestion behind an interface with the manual path as the initial
   implementation, so that a Waters/Empower import adapter can be added without changing template
   definitions, the calculation engine, or the UI's field model.
6. IF an area value is left blank THEN the system SHALL exclude it from replicate statistics rather
   than treating it as zero.

### Requirement 5: TRF Integration — Worksheet on a Test Line

**User Story:** As an Analyst, I want to open the correct calculation form directly from a TRF test
line, so that results flow into the TRF without re-keying.

#### Acceptance Criteria

1. WHEN a user adds a test line to a TRF and selects a Test that has one or more `Active` templates
   THEN the system SHALL offer those templates for selection.
2. WHEN a template is selected for a test line THEN the system SHALL create a worksheet instance
   bound to that test line and that template version, and SHALL pre-populate its context fields
   from the TRF header, the product/batch master, and the current session.
3. WHILE the parent TRF's status is `InProgress` an Analyst (or Admin) SHALL be able to enter and
   revise worksheet input and area values and SHALL see recalculated results.
4. WHEN a worksheet's reportable result is confirmed THEN the system SHALL write it to the parent
   test line's result field, so that existing TRF submission and release behaviour is unchanged.
5. IF a worksheet's blocking acceptance criteria fail THEN the system SHALL prevent confirming its
   reportable result and SHALL state which criteria failed.
6. IF a user attempts to modify a worksheet whose parent TRF is not `InProgress` (or
   `PendingADGLRelease` for a QA correction) THEN the system SHALL reject the request and SHALL
   leave the worksheet unchanged.
7. THE system SHALL preserve the existing free-text result entry path for test lines that have no
   template selected, so that this module is additive and does not break the current TRF flow.

### Requirement 6: Acceptance Criteria and System Suitability

**User Story:** As a QA reviewer, I want system suitability limits evaluated automatically, so that
an out-of-limit run cannot be quietly reported.

#### Acceptance Criteria

1. THE system SHALL evaluate each acceptance criterion declared on a template against the computed
   worksheet values and SHALL record each as pass or fail with the observed value and the limit.
2. THE system SHALL support criteria expressed as not-more-than, not-less-than, between, and equals
   comparisons against a computed field.
3. THE system SHALL distinguish blocking criteria (which prevent result confirmation) from advisory
   criteria (which warn only).
4. WHEN any criterion fails THEN the system SHALL display the failure prominently on the worksheet
   alongside the affected value.

### Requirement 7: PDF and File Attachments

**User Story:** As an Analyst, I want to attach chromatogram PDFs and raw data to a TRF after
testing, so that the complete data package lives with the record.

#### Acceptance Criteria

1. WHEN an Analyst (or Admin) uploads a file to a TRF whose status is `InProgress`,
   `PendingADGLRelease`, or `Released` THEN the system SHALL store it, linked to that TRF and
   optionally to a specific test line, capturing the original filename, content type, size,
   uploading user, and upload timestamp.
2. THE system SHALL accept PDF files and SHALL validate the declared content type and file
   signature; the system SHALL enforce a configurable maximum file size.
3. THE system SHALL reject files whose content type is not in the configured allow-list.
4. WHEN any authenticated user views a TRF THEN the system SHALL list its attachments and SHALL
   allow download.
5. WHEN an Analyst or Admin deletes an attachment on a TRF that is not yet `Released` THEN the
   system SHALL remove it and SHALL write an audit entry; attachments on a `Released` TRF SHALL NOT
   be deletable.
6. THE system SHALL store uploaded files outside the database on a configurable filesystem path,
   with generated storage names, and SHALL NOT expose or trust client-supplied paths.
7. THE system SHALL write an audit entry for every upload and deletion.

### Requirement 8: COA Generation with All Tests and Results

**User Story:** As a QA user, I want a COA that compiles every test and its result for a batch, so
that release documentation is generated rather than assembled by hand.

#### Acceptance Criteria

1. WHEN a QA user (or Admin) generates a COA for a batch THEN the system SHALL compile the released
   TRF results for that batch, listing each test, its specification, its reportable result, and its
   pass/fail determination against the specification.
2. THE system SHALL include COA header details: product, batch number, label claim, manufacturing
   and expiry/retest dates, pack details, AR and TRF references, and the release signature chain.
3. WHEN a COA is generated with a valid e-signature THEN the system SHALL capture an immutable COA
   snapshot, and SHALL NOT alter it if underlying master data later changes.
4. THE system SHALL render the COA as a browser-printable page, following the existing ATR and
   Stability print pattern.
5. IF a COA is requested for a batch with no released TRF results THEN the system SHALL reject the
   request with a validation error.
6. THE system SHALL include worksheet-derived results in the COA where a test line used a template,
   and free-text results where it did not.

### Requirement 9: Role-Based Access Control

**User Story:** As a system administrator, I want template and worksheet actions restricted to the
appropriate existing roles, so that no new roles are introduced.

#### Acceptance Criteria

1. WHEN a user creates, edits, or versions a Test Template THEN the system SHALL permit this only
   for the Admin role.
2. WHEN a user approves a Test Template THEN the system SHALL permit this only for Supervisor, QA,
   or Admin.
3. WHEN a user enters or revises worksheet values THEN the system SHALL permit this only for Analyst
   or Admin while the parent TRF is `InProgress`.
4. WHEN a user corrects worksheet values while the parent TRF is `PendingADGLRelease` THEN the
   system SHALL permit this only for QA or Admin.
5. WHEN a user generates or releases a COA THEN the system SHALL permit this only for QA or Admin.
6. WHEN any authenticated user views a template, worksheet, attachment, or COA THEN the system SHALL
   permit read access.

### Requirement 10: Audit Trail

**User Story:** As a QA reviewer, I want every template change, worksheet entry, and attachment
action audited, so that this module meets the same traceability standard as the rest of the system.

#### Acceptance Criteria

1. WHEN a Test Template is created, edited, versioned, approved, or deactivated THEN the system
   SHALL write an `AuditLog` entry capturing actor, action, timestamp, and old/new status.
2. WHEN worksheet input or area values are saved THEN the system SHALL write an `AuditLog` entry
   capturing the actor and the changed fields' old and new values.
3. WHEN a worksheet's reportable result is confirmed or corrected THEN the system SHALL write an
   `AuditLog` entry.
4. WHEN an attachment is uploaded or deleted, or a COA is generated, THEN the system SHALL write an
   `AuditLog` entry.

## Out of Scope (this iteration)

- **Live Waters/Empower integration.** Requirement 4 mandates the seam; the adapter itself is a
  follow-on. Areas are manually entered this iteration.
- **Automatic chromatogram PDF retrieval from Waters.** Attachments are manually uploaded.
- **The 5 bespoke archetypes** identified in the analysis — microbiological cylinder-plate bioassay
  (2 workbooks), Franz-cell IVRT (1), f1/f2 profile comparison (1), and the linearity/method
  qualification worksheet (1). These do not fit the generic schema and are deferred; see design.md
  §Archetype Fit.
- **Cross-test derived results** (drug-to-lipid ratio, free/entrapped drug) which consume other
  tests' approved results as inputs. Deferred pending confirmation of the double-normalisation
  question below.
- Electronic signature on individual worksheet field entry (the existing TRF gate signatures
  remain the control point).
- Migration of historical Excel results into the system.
- Server-rendered PDF generation (browser print is used, matching ATR/Stability).
- Instrument/column/working-standard master pickers beyond the existing resource masters.

## Dependencies and Assumptions Requiring Confirmation

- **Archetype priority.** The analysis recommends building the shared dilution-chain + master-
  equation + statistics engine first (covering ~16 workbooks: assay, multi-analyte content,
  saturation solubility, titrimetry, gravimetric, trace/nitrosamine), then Related Substances
  (6 workbooks), then Dissolution (7 workbooks), then Content Uniformity (2). **Confirm this
  ordering matches lab priority** — if a specific product's testing is the near-term driver, the
  order should follow that instead.
- **`Free & Entrapped Drug` formula.** The source sheet normalises by the total concentration twice
  in `free_mg_per_mL` and `entrapped_mg`. This looks like it may be unintended. **Requires lab
  confirmation before implementation** — flagged rather than silently reproduced or silently
  "fixed".
- **f1/f2 arithmetic.** The `F1F2 Calculation_sheet` only prepares the R(t)/T(t) tables; the actual
  f1/f2 computation is not present as a formula in the sheet. The standard definitions would be
  used, but **the lab should confirm** which convention and rounding they apply.
- **Rounding conventions.** The sheets mix `ROUND` and `TRUNC` at varying digit counts, sometimes
  mid-chain. These have been transcribed literally per template. **Any discrepancy against a
  validated reference result should be treated as a transcription bug and reported**, since these
  are GxP-reportable numbers.
- **Template validation/qualification.** Replacing validated Excel sheets with software
  calculations has GxP implications. Assumed the lab will run a parallel-verification exercise
  (same inputs through Excel and the LIMS) per template before it goes `Active` in production. The
  template approval gate in Requirement 1.3 exists to support that.
- **Attachment storage location and retention.** Assumed a configurable local filesystem path with
  no automatic retention policy this iteration. Confirm whether a network share or object store is
  required and whether retention/archival rules apply.
- **Specification source for COA pass/fail.** Assumed the existing `Specification` master supplies
  per-test limits. Confirm whether R&D COAs use the same specification records as QC release or a
  separate R&D specification set.
