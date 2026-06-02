"""
test_tools.py — Unit Tests for MCP Tool Functions
===================================================
Imports tool functions DIRECTLY from server.mcp_server.
No MCP server subprocess needed — plain function calls.

Run with:
    pytest tests/test_tools.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so 'server' is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.mcp_server import read_record, save_report, search_documents


# ---------------------------------------------------------------------------
# search_documents tests
# ---------------------------------------------------------------------------

class TestSearchDocuments:
    def test_returns_list_of_dicts(self):
        results = search_documents("database outage")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_result_has_required_keys(self):
        results = search_documents("SLA priority")
        for item in results:
            assert "filename" in item
            assert "score" in item
            assert "snippet" in item

    def test_top_k_respected(self):
        results = search_documents("network incident", top_k=2)
        assert len(results) <= 2

    def test_top_k_default_is_three(self):
        results = search_documents("backup recovery")
        assert len(results) <= 3

    def test_relevant_doc_ranked_first(self):
        results = search_documents("SLA response time resolution")
        # sla_policy.txt should be the top match
        assert results[0]["filename"] == "sla_policy.txt"

    def test_score_between_zero_and_one(self):
        results = search_documents("security incident ransomware")
        for item in results:
            assert 0.0 <= item["score"] <= 1.0

    def test_snippet_is_string(self):
        results = search_documents("patch management CVE")
        for item in results:
            assert isinstance(item["snippet"], str)

    def test_empty_query_returns_error(self):
        results = search_documents("")
        assert isinstance(results, list)
        assert "error" in results[0]

    def test_whitespace_query_returns_error(self):
        results = search_documents("   ")
        assert "error" in results[0]

    def test_query_too_long_returns_error(self):
        results = search_documents("a" * 501)
        assert "error" in results[0]
        assert "exceed 500 characters" in results[0]["error"]

    def test_no_matching_documents_returns_message(self):
        results = search_documents("xyzabcqwerty")
        assert isinstance(results, list)
        assert "message" in results[0]
        assert "No matching documents found" in results[0]["message"]


# ---------------------------------------------------------------------------
# read_record tests
# ---------------------------------------------------------------------------

class TestReadRecord:
    def test_valid_ticket_returns_dict(self):
        result = read_record("TICK-001")
        assert isinstance(result, dict)
        assert "error" not in result

    def test_valid_ticket_has_expected_fields(self):
        result = read_record("TICK-001")
        expected_fields = {
            "ticket_id", "created_date", "category", "status",
            "priority", "assigned_to", "assigned_group", "description",
        }
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

    def test_ticket_id_case_insensitive(self):
        result_upper = read_record("TICK-005")
        result_lower = read_record("tick-005")
        assert result_upper.get("ticket_id") == result_lower.get("ticket_id")

    def test_nonexistent_ticket_returns_error(self):
        result = read_record("TICK-999")
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_invalid_format_returns_validation_error(self):
        result = read_record("ABC-123")
        assert "error" in result
        assert "Invalid" in result["error"] or "format" in result["error"].lower()

    def test_empty_ticket_id_returns_error(self):
        result = read_record("")
        assert "error" in result

    def test_malformed_id_no_dash_returns_error(self):
        result = read_record("TICK001")
        assert "error" in result

    def test_known_p1_ticket(self):
        """TICK-004 is a known P1 Security ticket."""
        result = read_record("TICK-004")
        assert result.get("priority") == "P1"
        assert result.get("category") == "Security"

    def test_missing_database_file_returns_error(self, tmp_path, monkeypatch):
        import server.mcp_server as srv
        monkeypatch.setattr(srv, "_TICKETS_CSV", tmp_path / "nonexistent.csv")
        result = read_record("TICK-001")
        assert "error" in result
        assert any(term in result["error"].lower() for term in ("failed to read", "no ticket records", "not found"))


# ---------------------------------------------------------------------------
# save_report tests
# ---------------------------------------------------------------------------

class TestSaveReport:
    def test_saves_file_and_returns_path(self, tmp_path, monkeypatch):
        import server.mcp_server as srv
        monkeypatch.setattr(srv, "_OUTPUT_DIR", tmp_path)

        result = save_report("IT SLA Report", "# Test Report\n\nHello.")
        assert result.endswith("it_sla_report.md")
        assert Path(result).exists()

    def test_saved_content_matches_input(self, tmp_path, monkeypatch):
        import server.mcp_server as srv
        monkeypatch.setattr(srv, "_OUTPUT_DIR", tmp_path)

        content = "# My Report\n\nSome **bold** text."
        result = save_report("My Report", content)
        written = Path(result).read_text(encoding="utf-8")
        assert written == content

    def test_empty_title_returns_error(self):
        result = save_report("", "content")
        assert "Error" in result
        assert "title" in result.lower()

    def test_whitespace_title_returns_error(self):
        result = save_report("   ", "content")
        assert "Error" in result

    def test_empty_content_returns_error(self):
        result = save_report("Title", "")
        assert "Error" in result
        assert "content" in result.lower()

    def test_whitespace_content_returns_error(self):
        result = save_report("Title", "   ")
        assert "Error" in result

    def test_slugify_handles_special_characters(self, tmp_path, monkeypatch):
        import server.mcp_server as srv
        monkeypatch.setattr(srv, "_OUTPUT_DIR", tmp_path)

        result = save_report("  Emergency - recovery!  ", "content")
        assert result.endswith("emergency_-_recovery.md")
        assert Path(result).exists()
