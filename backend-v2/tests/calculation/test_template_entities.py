"""
Unit tests for the TestTemplate / TestWorksheet domain entities.

Covers the lifecycle guards, the worksheet edit-mode mapping, and
**Property 10: Template versioning preserves executed worksheets** — the rule
that branching a new version must never disturb the approved one.
"""
from datetime import datetime, timezone

import pytest

from src.domain.entities.test_template import (
    TemplateStatus,
    WorksheetEditMode,
    WorksheetStatus,
)

#  Aliased for readability against the `TestXxx` test-class names below; the
#  pytest collection collision itself is handled in pyproject.toml.
from src.domain.entities.test_template import TestTemplate as TemplateEntity
from src.domain.entities.test_template import TestWorksheet as WorksheetEntity
from src.domain.services.template_code_generator import TemplateCodeGenerator

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)

DEFINITION = {
    "resultRef": "g.out",
    "groups": [
        {
            "key": "g",
            "kind": "singleton",
            "fields": [
                {"key": "a", "kind": "input"},
                {"key": "out", "kind": "calculated", "expression": "a * 2"},
            ],
        }
    ],
}


def _template(**overrides) -> TemplateEntity:
    base = dict(
        code="TPL-A1-0001",
        name="Assay by HPLC",
        archetype="A1",
        test_id=1,
        definition=DEFINITION,
        created_by="admin",
        modified_by="admin",
    )
    base.update(overrides)
    return TemplateEntity(**base)


class TestTemplateLifecycle:
    def test_new_template_starts_as_draft_version_1(self):
        t = _template()
        assert t.status == TemplateStatus.DRAFT.value
        assert t.version == 1
        assert t.is_selectable is False

    def test_definition_editable_while_draft(self):
        t = _template()
        assert t.can_edit_definition() is True
        t.update_definition({"groups": []}, "admin")
        assert t.definition == {"groups": []}

    def test_definition_not_editable_once_active(self):
        t = _template(status=TemplateStatus.ACTIVE.value)
        assert t.can_edit_definition() is False
        with pytest.raises(ValueError, match="only be edited while Draft"):
            t.update_definition({"groups": []}, "admin")

    def test_submit_requires_a_definition(self):
        t = _template(definition={})
        assert t.can_submit() is False
        with pytest.raises(ValueError, match="Draft with a definition"):
            t.submit_for_approval("admin")

    def test_submit_moves_to_pending_approval(self):
        t = _template()
        t.submit_for_approval("admin")
        assert t.status == TemplateStatus.PENDING_APPROVAL.value

    def test_approve_requires_pending_approval(self):
        t = _template()
        with pytest.raises(ValueError, match="requires PendingApproval"):
            t.approve("qa", NOW)

    def test_approve_activates_and_records_signature(self):
        t = _template()
        t.submit_for_approval("admin")
        t.approve("qa", NOW)
        assert t.status == TemplateStatus.ACTIVE.value
        assert t.approved_by == "qa"
        assert t.approved_at == NOW
        assert t.is_selectable is True

    def test_reject_returns_to_draft(self):
        t = _template()
        t.submit_for_approval("admin")
        t.reject("qa")
        assert t.status == TemplateStatus.DRAFT.value
        # Editable again after rejection.
        assert t.can_edit_definition() is True

    def test_deactivate_requires_active(self):
        t = _template()
        with pytest.raises(ValueError, match="Only an Active template"):
            t.deactivate("admin")

    def test_deactivated_template_is_not_selectable(self):
        t = _template(status=TemplateStatus.ACTIVE.value)
        t.deactivate("admin")
        assert t.status == TemplateStatus.INACTIVE.value
        assert t.is_selectable is False

    def test_only_approved_templates_can_be_versioned(self):
        assert _template().can_version() is False
        assert _template(status=TemplateStatus.PENDING_APPROVAL.value).can_version() is False
        assert _template(status=TemplateStatus.ACTIVE.value).can_version() is True
        assert _template(status=TemplateStatus.INACTIVE.value).can_version() is True

    def test_versioning_a_draft_raises(self):
        with pytest.raises(ValueError, match="only be branched from an approved template"):
            _template().new_version("admin")


class TestVersionIsolation:
    """
    Property 10: branching a new version must leave the approved version — and
    anything already executed against it — completely untouched.
    """

    def test_new_version_increments_and_returns_to_draft(self):
        active = _template(status=TemplateStatus.ACTIVE.value, version=3)
        draft = active.new_version("admin")
        assert draft.version == 4
        assert draft.status == TemplateStatus.DRAFT.value
        assert draft.code == active.code

    def test_source_template_is_unchanged_by_versioning(self):
        active = _template(status=TemplateStatus.ACTIVE.value, approved_by="qa", approved_at=NOW)
        before = (
            active.status,
            active.version,
            active.approved_by,
            active.approved_at,
            dict(active.definition),
        )
        active.new_version("admin")
        assert (
            active.status,
            active.version,
            active.approved_by,
            active.approved_at,
            dict(active.definition),
        ) == before

    def test_new_version_does_not_inherit_the_approval_signature(self):
        active = _template(status=TemplateStatus.ACTIVE.value, approved_by="qa", approved_at=NOW)
        draft = active.new_version("admin")
        assert draft.approved_by is None
        assert draft.approved_at is None

    def test_definition_is_copied_not_aliased(self):
        """
        The crux of Property 10: if the new draft aliased the approved
        definition, editing the draft would silently change what every executed
        worksheet resolves against.
        """
        active = _template(status=TemplateStatus.ACTIVE.value)
        draft = active.new_version("admin")

        assert draft.definition is not active.definition
        assert draft.definition["groups"] is not active.definition["groups"]
        assert draft.definition["groups"][0] is not active.definition["groups"][0]
        assert (
            draft.definition["groups"][0]["fields"]
            is not active.definition["groups"][0]["fields"]
        )

    def test_mutating_the_draft_definition_leaves_the_active_one_intact(self):
        active = _template(status=TemplateStatus.ACTIVE.value)
        draft = active.new_version("admin")

        draft.definition["groups"][0]["fields"][1]["expression"] = "a * 999"
        draft.definition["groups"].append({"key": "extra", "kind": "singleton", "fields": []})

        assert active.definition["groups"][0]["fields"][1]["expression"] == "a * 2"
        assert len(active.definition["groups"]) == 1

    def test_superseded_pointer_records_history(self):
        active = _template(status=TemplateStatus.ACTIVE.value)
        active.mark_superseded_by(42, "qa")
        assert active.superseded_by_id == 42

    def test_a_versioned_chain_keeps_one_code(self):
        v1 = _template(status=TemplateStatus.ACTIVE.value)
        v2 = v1.new_version("admin")
        v2.submit_for_approval("admin")
        v2.approve("qa", NOW)
        v3 = v2.new_version("admin")
        assert {v1.code, v2.code, v3.code} == {"TPL-A1-0001"}
        assert [v1.version, v2.version, v3.version] == [1, 2, 3]


class TestWorksheetEditMode:
    """Requirements 5.3 / 5.6: the parent TRF's status decides what is allowed."""

    @pytest.mark.parametrize(
        "trf_status,expected",
        [
            ("InProgress", WorksheetEditMode.ENTRY),
            ("PendingADGLRelease", WorksheetEditMode.CORRECTION),
            ("Draft", None),
            ("PendingFDGLApproval", None),
            ("PendingADGLAcceptance", None),
            ("PendingAnalystAcceptance", None),
            ("Released", None),
            ("Rejected", None),
            ("ReferredBack", None),
        ],
    )
    def test_edit_mode_mapping(self, trf_status, expected):
        assert WorksheetEntity.edit_mode_for(trf_status) is expected

    def test_can_edit_values_follows_the_mapping(self):
        ws = WorksheetEntity(trf_test_line_id=1, template_id=1)
        assert ws.can_edit_values("InProgress") is True
        assert ws.can_edit_values("PendingADGLRelease") is True
        assert ws.can_edit_values("Released") is False

    def test_confirm_is_only_permitted_during_entry(self):
        ws = WorksheetEntity(trf_test_line_id=1, template_id=1)
        assert ws.can_confirm("InProgress") is True
        # A QA correction may change values but not re-confirm.
        assert ws.can_confirm("PendingADGLRelease") is False
        assert ws.can_confirm("Released") is False

    def test_unknown_trf_status_permits_nothing(self):
        assert WorksheetEntity.edit_mode_for("SomeFutureStatus") is None


class TestWorksheetValues:
    def test_new_worksheet_starts_in_progress(self):
        ws = WorksheetEntity(trf_test_line_id=1, template_id=1)
        assert ws.status == WorksheetStatus.IN_PROGRESS.value
        assert ws.is_confirmed is False
        assert ws.reportable_result is None

    def test_set_values_stores_copies_not_references(self):
        ws = WorksheetEntity(trf_test_line_id=1, template_id=1)
        context = {"label_claim": 50.0}
        groups = {"std": [{"area": 100.0}]}
        ws.set_values(context, groups, "analyst")

        context["label_claim"] = 999.0
        groups["std"][0]["area"] = 999.0

        assert ws.context_values["label_claim"] == 50.0
        assert ws.group_values["std"][0]["area"] == 100.0

    def test_set_values_with_none_leaves_that_side_untouched(self):
        ws = WorksheetEntity(trf_test_line_id=1, template_id=1)
        ws.set_values({"a": 1.0}, {"g": [{"b": 2.0}]}, "analyst")
        ws.set_values(None, {"g": [{"b": 3.0}]}, "analyst")
        assert ws.context_values == {"a": 1.0}
        assert ws.group_values["g"][0]["b"] == 3.0

    def test_confirm_freezes_snapshot_and_publishes_result(self):
        ws = WorksheetEntity(trf_test_line_id=1, template_id=1)
        snapshot = {"values": {"g.out": 108.838}, "criteria": []}
        ws.confirm("analyst", NOW, snapshot, "108.838")
        assert ws.is_confirmed is True
        assert ws.reportable_result == "108.838"
        assert ws.confirmed_by == "analyst"
        assert ws.confirmed_at == NOW
        assert ws.computed_snapshot == snapshot

    def test_reopen_clears_the_signature_but_retains_the_snapshot(self):
        ws = WorksheetEntity(trf_test_line_id=1, template_id=1)
        snapshot = {"values": {"g.out": 1.0}}
        ws.confirm("analyst", NOW, snapshot, "1.0")
        ws.reopen("qa")
        assert ws.status == WorksheetStatus.IN_PROGRESS.value
        assert ws.confirmed_by is None
        assert ws.confirmed_at is None
        # Retained so a released TRF never has a result with no supporting snapshot.
        assert ws.computed_snapshot == snapshot

    def test_version_binding_is_recorded(self):
        ws = WorksheetEntity(trf_test_line_id=1, template_id=7, template_version=3)
        assert (ws.template_id, ws.template_version) == (7, 3)


class TestTemplateCodeGenerator:
    def test_generates_sequential_codes_per_archetype(self):
        assert TemplateCodeGenerator.generate("A1", 0) == "TPL-A1-0001"
        assert TemplateCodeGenerator.generate("A1", 4) == "TPL-A1-0005"

    def test_archetype_is_normalized(self):
        assert TemplateCodeGenerator.generate("a6a", 0) == "TPL-A6A-0001"
        assert TemplateCodeGenerator.generate("Assay HPLC", 0) == "TPL-ASSAY-HPLC-0001"

    def test_blank_archetype_falls_back(self):
        assert TemplateCodeGenerator.generate("", 0) == "TPL-GEN-0001"
        assert TemplateCodeGenerator.generate("---", 0) == "TPL-GEN-0001"

    def test_prefix_matches_generated_code(self):
        prefix = TemplateCodeGenerator.archetype_prefix("A4")
        assert TemplateCodeGenerator.generate("A4", 0).startswith(prefix)

    def test_sequence_is_zero_padded_to_four_digits(self):
        assert TemplateCodeGenerator.generate("A1", 9998) == "TPL-A1-9999"
