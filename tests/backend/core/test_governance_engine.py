"""
Tests for backend/core/governance_engine.py
"""

import importlib
import json
import pathlib

import pytest

# ── Direct import of the module under test ──────────────────────────
_spec = importlib.util.spec_from_file_location(
    "governance_engine",
    str(pathlib.Path(__file__).resolve().parents[3] / "backend" / "core" / "governance_engine.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

create_approval = _mod.create_approval
get_approvals = _mod.get_approvals
respond_to_approval = _mod.respond_to_approval
record_kpi = _mod.record_kpi
get_kpi_scores = _mod.get_kpi_scores
get_kpi_dashboard = _mod.get_kpi_dashboard
COMPLIANCE_PRESETS = _mod.COMPLIANCE_PRESETS
get_compliance_presets = _mod.get_compliance_presets
apply_compliance_preset = _mod.apply_compliance_preset
get_project_rules = _mod.get_project_rules
set_project_rules = _mod.set_project_rules


# ═══════════════════════════════════════════════════════════════════
#  APPROVAL WORKFLOW
# ═══════════════════════════════════════════════════════════════════

class TestApprovalWorkflow:

    @pytest.fixture(autouse=True)
    def reset_approvals(self):
        _mod._approvals.clear()
        _mod._approval_counter = 0

    def test_create_approval_returns_correct_structure(self):
        result = create_approval(title="Deploy v2", description="Production deploy")
        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["title"] == "Deploy v2"
        assert result["description"] == "Production deploy"
        assert result["status"] == "pending"
        assert result["responses"] == []
        assert "created_at" in result

    def test_multiple_approvals_get_incrementing_ids(self):
        a1 = create_approval(title="First", description="d1")
        a2 = create_approval(title="Second", description="d2")
        a3 = create_approval(title="Third", description="d3")
        assert a1["id"] == 1
        assert a2["id"] == 2
        assert a3["id"] == 3

    def test_get_approvals_returns_all(self):
        create_approval(title="A", description="d")
        create_approval(title="B", description="d")
        result = get_approvals()
        assert len(result) == 2

    def test_get_approvals_filters_by_status(self):
        create_approval(title="A", description="d")
        a2 = create_approval(title="B", description="d")
        respond_to_approval(a2["id"], action="approve")

        pending = get_approvals(status="pending")
        approved = get_approvals(status="approved")
        assert len(pending) == 1
        assert pending[0]["title"] == "A"
        assert len(approved) == 1
        assert approved[0]["title"] == "B"

    def test_get_approvals_filters_by_project_id(self):
        create_approval(title="A", description="d", project_id="proj-1")
        create_approval(title="B", description="d", project_id="proj-2")
        create_approval(title="C", description="d", project_id="proj-1")

        result = get_approvals(project_id="proj-1")
        assert len(result) == 2
        assert all(a["project_id"] == "proj-1" for a in result)

    def test_respond_approve_sets_status_and_resolved_at(self):
        a = create_approval(title="X", description="d")
        result = respond_to_approval(a["id"], action="approve", reason="LGTM")
        assert result["status"] == "approved"
        assert "resolved_at" in result

    def test_respond_deny_sets_status(self):
        a = create_approval(title="X", description="d")
        result = respond_to_approval(a["id"], action="deny", reason="Not ready")
        assert result["status"] == "denied"
        assert "resolved_at" in result

    def test_respond_discuss_sets_status(self):
        a = create_approval(title="X", description="d")
        result = respond_to_approval(a["id"], action="discuss", reason="Need more info")
        assert result["status"] == "discussing"
        assert "resolved_at" not in result

    def test_respond_to_nonexistent_approval(self):
        result = respond_to_approval(approval_id=999, action="approve")
        assert result == {"error": "Approval not found"}

    def test_response_appended_to_responses_list(self):
        a = create_approval(title="X", description="d")
        respond_to_approval(a["id"], action="discuss", reason="first")
        respond_to_approval(a["id"], action="approve", reason="second")

        approvals = get_approvals()
        target = approvals[0]
        assert len(target["responses"]) == 2
        assert target["responses"][0]["action"] == "discuss"
        assert target["responses"][0]["reason"] == "first"
        assert target["responses"][1]["action"] == "approve"
        assert target["responses"][1]["reason"] == "second"
        assert "timestamp" in target["responses"][0]


# ═══════════════════════════════════════════════════════════════════
#  KPI SCORING
# ═══════════════════════════════════════════════════════════════════

class TestKPIScoring:

    @pytest.fixture(autouse=True)
    def reset_kpis(self):
        _mod._kpi_scores.clear()

    def test_record_kpi_creates_entry(self):
        record_kpi(component="parser", feature="tokenize", passed=True, layer=1)
        scores = get_kpi_scores()
        assert "parser/tokenize" in scores["scores"]
        entry = scores["scores"]["parser/tokenize"]
        assert entry["component"] == "parser"
        assert entry["feature"] == "tokenize"

    def test_record_kpi_passed_true_score_100(self):
        record_kpi(component="parser", feature="tokenize", passed=True, layer=1)
        entry = get_kpi_scores()["scores"]["parser/tokenize"]
        assert entry["score"] == 100.0

    def test_record_kpi_passed_false_score_0(self):
        record_kpi(component="parser", feature="tokenize", passed=False, layer=1)
        entry = get_kpi_scores()["scores"]["parser/tokenize"]
        assert entry["score"] == 0.0

    def test_multiple_records_update_score(self):
        record_kpi(component="parser", feature="tokenize", passed=True, layer=1)
        record_kpi(component="parser", feature="tokenize", passed=True, layer=2)
        record_kpi(component="parser", feature="tokenize", passed=False, layer=3)
        entry = get_kpi_scores()["scores"]["parser/tokenize"]
        # 2 passed / 3 total = 66.7%
        assert entry["score"] == 66.7

    def test_layers_passed_tracks_layers(self):
        record_kpi(component="parser", feature="tokenize", passed=True, layer=1)
        record_kpi(component="parser", feature="tokenize", passed=False, layer=2)
        record_kpi(component="parser", feature="tokenize", passed=True, layer=3)
        entry = get_kpi_scores()["scores"]["parser/tokenize"]
        assert entry["layers_passed"] == [1, 3]

    def test_get_kpi_scores_returns_average_and_trust(self):
        record_kpi(component="parser", feature="tokenize", passed=True, layer=1)
        record_kpi(component="engine", feature="compile", passed=False, layer=1)
        scores = get_kpi_scores()
        # parser/tokenize=100, engine/compile=0 → avg=50
        assert scores["average_score"] == 50.0
        assert scores["trust_score"] == 0.5
        assert scores["total_features"] == 2

    def test_get_kpi_scores_filters_by_component(self):
        record_kpi(component="parser", feature="tokenize", passed=True, layer=1)
        record_kpi(component="engine", feature="compile", passed=False, layer=1)
        scores = get_kpi_scores(component="parser")
        assert scores["total_features"] == 1
        assert "parser/tokenize" in scores["scores"]
        assert "engine/compile" not in scores["scores"]

    def test_get_kpi_scores_no_data_default_trust(self):
        scores = get_kpi_scores()
        assert scores["trust_score"] == 0.5
        assert scores["total_features"] == 0
        assert scores["average_score"] == 0

    def test_get_kpi_dashboard_groups_by_component(self):
        record_kpi(component="parser", feature="tokenize", passed=True, layer=1)
        record_kpi(component="parser", feature="lex", passed=True, layer=1)
        record_kpi(component="engine", feature="compile", passed=False, layer=1)
        dash = get_kpi_dashboard()
        assert "parser" in dash["components"]
        assert "engine" in dash["components"]
        assert dash["total_components"] == 2
        assert dash["components"]["parser"]["features"] == 2
        assert dash["components"]["parser"]["average_score"] == 100.0
        assert dash["components"]["engine"]["features"] == 1
        assert dash["components"]["engine"]["average_score"] == 0.0


# ═══════════════════════════════════════════════════════════════════
#  COMPLIANCE PRESETS
# ═══════════════════════════════════════════════════════════════════

class TestCompliancePresets:

    def test_get_compliance_presets_structure(self):
        result = get_compliance_presets()
        assert "presets" in result
        assert "total" in result
        assert result["total"] == len(COMPLIANCE_PRESETS)

    def test_compliance_presets_expected_keys(self):
        expected = {
            "iso_27001", "gdpr", "soc2", "owasp", "nist_csf",
            "pci_dss", "hipaa", "iso_22301", "iso_42001",
        }
        assert set(COMPLIANCE_PRESETS.keys()) == expected

    def test_each_preset_has_name_and_at_least_5_rules(self):
        for key, preset in COMPLIANCE_PRESETS.items():
            assert "name" in preset, f"{key} missing 'name'"
            assert "rules" in preset, f"{key} missing 'rules'"
            assert isinstance(preset["rules"], list)
            assert len(preset["rules"]) >= 5, f"{key} has fewer than 5 rules"

    def test_apply_unknown_preset_returns_error(self):
        result = apply_compliance_preset(project_id="proj-1", preset_name="unknown_xyz")
        assert "error" in result

    @pytest.fixture
    def governance_tmp(self, tmp_path):
        original = _mod.DATA_DIR
        _mod.DATA_DIR = tmp_path
        yield tmp_path
        _mod.DATA_DIR = original

    def test_apply_valid_preset_creates_file(self, governance_tmp):
        result = apply_compliance_preset(project_id="proj-1", preset_name="gdpr")
        assert result["applied"] is True
        assert result["preset"] == "gdpr"
        assert result["rules_count"] == len(COMPLIANCE_PRESETS["gdpr"]["rules"])

        created = governance_tmp / "projects" / "proj-1" / "governance" / "compliance_gdpr.md"
        assert created.exists()
        content = created.read_text()
        assert "GDPR Data Protection" in content

    def test_get_project_rules_with_tmp(self, governance_tmp):
        rules = get_project_rules("proj-test")
        assert rules["project_id"] == "proj-test"
        assert rules["rules"] == []
        assert rules["total"] == 0

    def test_set_project_rules_with_tmp(self, governance_tmp):
        result = set_project_rules("proj-test", {"max_retries": 3})
        assert result["saved"] is True
        assert result["project_id"] == "proj-test"

        rules = get_project_rules("proj-test")
        assert rules["config"]["max_retries"] == 3
        assert "updated_at" in rules["config"]

    def test_set_then_get_project_rules_roundtrip(self, governance_tmp):
        set_project_rules("proj-rt", {"policy": "strict", "reviewers": 2})
        rules = get_project_rules("proj-rt")
        assert rules["config"]["policy"] == "strict"
        assert rules["config"]["reviewers"] == 2

    def test_apply_preset_then_get_project_rules(self, governance_tmp):
        apply_compliance_preset(project_id="proj-combo", preset_name="iso_27001")
        rules = get_project_rules("proj-combo")
        assert rules["total"] == 1
        assert rules["rules"][0]["name"] == "compliance_iso_27001"
