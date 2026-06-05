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

class CrewResult:
    def __init__(self, result, output_dir, traces_dir, before_traces):
        self.result = result
        self.output_dir = output_dir
        self.traces_dir = traces_dir
        self.before_traces = before_traces


@pytest.fixture(scope="module")
def crew_run_result():
    """Run the crew exactly once and store results for module-wide assertions."""
    from crew.crew import run_crew

    _ROOT = Path(__file__).parent.parent
    output_dir = _ROOT / "output"
    traces_dir = _ROOT / "traces"

    # Remove all .md files in output directory to ensure we confirm this run created it
    if output_dir.exists():
        for md_file in output_dir.glob("*.md"):
            try:
                md_file.unlink()
            except Exception:
                pass

    # Count traces before
    before_traces = set(traces_dir.glob("trace_*.json")) if traces_dir.exists() else set()

    result = run_crew(_FIXED_QUESTION)

    return CrewResult(result, output_dir, traces_dir, before_traces)


@skip_if_no_llm
def test_crew_returns_non_empty_string(crew_run_result):
    """Crew should return a non-empty string for the fixed question."""
    result = crew_run_result.result
    assert isinstance(result, str), "Result must be a string"
    assert len(result.strip()) > 0, "Result must not be empty"


@skip_if_no_llm
def test_crew_result_mentions_p1(crew_run_result):
    """Result should reference P1 since the question explicitly asks about it."""
    result = crew_run_result.result
    assert "P1" in result, "Result should mention P1 priority"


@skip_if_no_llm
def test_crew_result_mentions_sla(crew_run_result):
    """Result should reference SLA since the question explicitly asks about it."""
    result = crew_run_result.result
    assert any(kw in result for kw in ("SLA", "sla", "response time", "resolution")), \
        "Result should mention SLA or response/resolution time"


@skip_if_no_llm
def test_crew_report_saved_to_output(crew_run_result):
    """Writer agent should have created a report file in output/."""
    md_files = list(crew_run_result.output_dir.glob("*.md"))
    assert len(md_files) >= 1, "A markdown report should be created by the Writer in output/"
    report_path = md_files[0]
    content = report_path.read_text(encoding="utf-8")
    assert len(content.strip()) > 0, "Saved report should not be empty"


@skip_if_no_llm
def test_crew_report_contains_citation(crew_run_result):
    """Report should contain at least one inline citation (filename or ticket ID)."""
    md_files = list(crew_run_result.output_dir.glob("*.md"))
    assert len(md_files) >= 1, "A markdown report should be created by the Writer"
    report_path = md_files[0]
    content = report_path.read_text(encoding="utf-8")
    # Citations look like [sla_policy.txt] or [TICK-001]
    import re
    citation_pattern = re.compile(r"\[(TICK-\d+|[\w_]+\.txt)\]")
    assert citation_pattern.search(content), \
        "Report should contain at least one citation like [sla_policy.txt] or [TICK-001]"


@skip_if_no_llm
def test_crew_trace_saved(crew_run_result):
    """A trace file should appear in traces/ after the crew runs."""
    after_traces = set(crew_run_result.traces_dir.glob("trace_*.json"))
    new_traces = after_traces - crew_run_result.before_traces
    assert len(new_traces) >= 1, "A trace file should be saved to traces/"
