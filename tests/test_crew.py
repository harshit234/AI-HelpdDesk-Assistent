"""
test_crew.py — End-to-End Crew Integration Test
=================================================
Runs the full Researcher → Writer → Verifier crew on a single fixed question.
Requires the LLM to be reachable (Ollama running locally, or API key set).

Automatically skipped if no LLM is configured (OPENAI_API_KEY not set
AND Ollama not detected), so CI pipelines don't fail without credentials.

Run with:
    pytest tests/test_crew.py -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Skip condition — skip if no LLM is available
# ---------------------------------------------------------------------------

def _ollama_available() -> bool:
    """Return True if Ollama appears to be running locally."""
    try:
        import urllib.request

        urllib.request.urlopen(
            "http://localhost:11434/api/tags", timeout=2
        )
        return True
    except Exception:
        return False


_has_openai_key = bool(os.getenv("OPENAI_API_KEY", "").strip()) and \
                  os.getenv("OPENAI_API_KEY", "").strip() not in ("", "ollama")
_has_gemini_key = bool(os.getenv("GEMINI_API_KEY", "").strip())
_has_ollama     = _ollama_available()

_is_python_314_or_greater = sys.version_info >= (3, 14)

_llm_available = (_has_openai_key or _has_gemini_key or _has_ollama) and not _is_python_314_or_greater

skip_if_no_llm = pytest.mark.skipif(
    not _llm_available,
    reason=(
        "Crew integration tests are skipped on Python 3.14+ due to Pydantic V1/ChromaDB incompatibility, "
        "or if no LLM is configured."
    ),
)

# ---------------------------------------------------------------------------
# Fixed test question
# ---------------------------------------------------------------------------

_FIXED_QUESTION = "What is the SLA for a P1 incident and how many P1 tickets are currently open?"

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@skip_if_no_llm
def test_crew_returns_non_empty_string():
    """Crew should return a non-empty string for the fixed question."""
    from crew.crew import run_crew

    result = run_crew(_FIXED_QUESTION)
    assert isinstance(result, str), "Result must be a string"
    assert len(result.strip()) > 0, "Result must not be empty"


@skip_if_no_llm
def test_crew_result_mentions_p1():
    """Result should reference P1 since the question explicitly asks about it."""
    from crew.crew import run_crew

    result = run_crew(_FIXED_QUESTION)
    assert "P1" in result, "Result should mention P1 priority"


@skip_if_no_llm
def test_crew_result_mentions_sla():
    """Result should reference SLA since the question explicitly asks about it."""
    from crew.crew import run_crew

    result = run_crew(_FIXED_QUESTION)
    assert any(kw in result for kw in ("SLA", "sla", "response time", "resolution")), \
        "Result should mention SLA or response/resolution time"


@skip_if_no_llm
def test_crew_report_saved_to_output():
    """Writer agent should have created output/report.md."""
    from crew.crew import run_crew

    _ROOT = Path(__file__).parent.parent
    report_path = _ROOT / "output" / "report.md"

    # Remove stale file if it exists so we confirm this run created it
    if report_path.exists():
        report_path.unlink()

    run_crew(_FIXED_QUESTION)

    assert report_path.exists(), "output/report.md should be created by the Writer"
    content = report_path.read_text(encoding="utf-8")
    assert len(content.strip()) > 0, "output/report.md should not be empty"


@skip_if_no_llm
def test_crew_report_contains_citation():
    """Report should contain at least one inline citation (filename or ticket ID)."""
    from crew.crew import run_crew
    import re

    _ROOT = Path(__file__).parent.parent
    report_path = _ROOT / "output" / "report.md"

    run_crew(_FIXED_QUESTION)

    content = report_path.read_text(encoding="utf-8")
    # Citations look like [sla_policy.txt] or [TICK-001]
    citation_pattern = re.compile(r"\[(TICK-\d+|[\w_]+\.txt)\]")
    assert citation_pattern.search(content), \
        "Report should contain at least one citation like [sla_policy.txt] or [TICK-001]"


@skip_if_no_llm
def test_crew_trace_saved():
    """A trace file should appear in traces/ after the crew runs."""
    from crew.crew import run_crew

    _ROOT = Path(__file__).parent.parent
    traces_dir = _ROOT / "traces"

    # Count before
    before = set(traces_dir.glob("trace_*.json")) if traces_dir.exists() else set()

    run_crew(_FIXED_QUESTION)

    after = set(traces_dir.glob("trace_*.json"))
    new_traces = after - before
    assert len(new_traces) >= 1, "A trace file should be saved to traces/"
