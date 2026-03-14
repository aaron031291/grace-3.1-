"""
End-to-end test: file write → Genesis Key + domain lineage metadata.

Codebase (operational) → Domain folder (governance).
"""

import os
import pytest
from pathlib import Path


def test_infer_domain_from_path():
    """Domain inference from path patterns."""
    from core.domain_lineage_bridge import infer_domain_from_path

    assert infer_domain_from_path("/a/b/data/projects/microsoft/backend/foo.py") == "microsoft"
    assert infer_domain_from_path("C:\\x\\data\\projects\\apple\\frontend\\x.js") == "apple"
    assert infer_domain_from_path("/kb/domains/ai_ethics/documents/x.md") == "ai_ethics"
    assert infer_domain_from_path("/tmp/other/bar.py") is None


def test_log_lineage_creates_metadata_file(tmp_path):
    """log_lineage creates domain/metadata/lineage.jsonl."""
    # Patch KB path to use tmp_path
    import core.domain_lineage_bridge as dlb
    kb_domains = tmp_path / "kb" / "domains"
    kb_domains.mkdir(parents=True)
    orig = dlb._KB_DOMAINS
    dlb._KB_DOMAINS = kb_domains

    try:
        dlb.log_lineage(
            domain="test-domain",
            file_path="backend/foo.py",
            operation_type="modify",
            source="test",
        )
        lineage_file = kb_domains / "test-domain" / "metadata" / "lineage.jsonl"
        assert lineage_file.exists()
        lines = lineage_file.read_text().strip().split("\n")
        assert len(lines) == 1
        import json
        rec = json.loads(lines[0])
        assert rec["file_path"] == "backend/foo.py"
        assert rec["operation_type"] == "modify"
        assert "timestamp" in rec
    finally:
        dlb._KB_DOMAINS = orig


def test_route_file_write_logs_lineage(tmp_path):
    """route_file_write → file saved + lineage in domain metadata."""
    import core.environment as env
    env.PROJECTS_DIR = tmp_path / "projects"
    env.PROJECTS_DIR.mkdir(parents=True)

    import core.domain_lineage_bridge as dlb
    kb_domains = tmp_path / "kb" / "domains"
    kb_domains.mkdir(parents=True)
    orig_kb = dlb._KB_DOMAINS
    dlb._KB_DOMAINS = kb_domains

    try:
        env.set_environment("acme-corp", "default")
        result = env.route_file_write(
            relative_path="backend/main.py",
            content="print('hello')",
            source="dev_tab",
        )
        assert result["saved"] is True
        assert result["environment"] == "acme-corp"

        lineage_file = kb_domains / "acme-corp" / "metadata" / "lineage.jsonl"
        assert lineage_file.exists()
        lines = [l for l in lineage_file.read_text().strip().split("\n") if l]
        assert len(lines) >= 1
        import json
        rec = json.loads(lines[-1])
        assert "backend" in rec["file_path"] or "main.py" in rec["file_path"]
    finally:
        dlb._KB_DOMAINS = orig_kb


def test_get_lineage_for_domain(tmp_path):
    """get_lineage_for_domain returns recent records."""
    import core.domain_lineage_bridge as dlb
    kb_domains = tmp_path / "kb2" / "domains"
    kb_domains.mkdir(parents=True)
    orig = dlb._KB_DOMAINS
    dlb._KB_DOMAINS = kb_domains

    try:
        dlb.log_lineage("audit-me", "x.py", "modify", source="test")
        dlb.log_lineage("audit-me", "y.py", "add", source="test")
        records = dlb.get_lineage_for_domain("audit-me", limit=10)
        assert len(records) == 2
        assert records[0]["file_path"] in ("x.py", "y.py")
    finally:
        dlb._KB_DOMAINS = orig


def test_log_lineage_from_path_infers_domain(tmp_path):
    """log_lineage_from_path infers domain from path."""
    import core.domain_lineage_bridge as dlb
    kb_domains = tmp_path / "kb3" / "domains"
    kb_domains.mkdir(parents=True)
    orig = dlb._KB_DOMAINS
    dlb._KB_DOMAINS = kb_domains

    try:
        path = str(tmp_path / "data" / "projects" / "client-beta" / "src" / "app.py")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("# app")
        out = dlb.log_lineage_from_path(path, operation_type="modify", source="workspace")
        assert out is not None
        lineage_file = kb_domains / "client-beta" / "metadata" / "lineage.jsonl"
        assert lineage_file.exists()
    finally:
        dlb._KB_DOMAINS = orig


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
