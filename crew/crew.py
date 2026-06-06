"""
crew.py — Crew Assembly and CLI Entry Point
=============================================
Connects to the MCP server via MCPServerAdapter (stdio transport),
builds the three-agent sequential crew, and runs it.

Usage (CLI):
    python -m crew.crew
    python -m crew.crew --question "What is the SLA for P1 tickets?"

Usage (programmatic):
    from crew.crew import run_crew
    result = run_crew("What is the SLA for P1 tickets?")
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from crewai import Crew, Process
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

from crew.agents import make_researcher, make_verifier, make_writer
from crew.tasks import make_research_task, make_verify_task, make_write_task

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent.parent
_TRACES_DIR = _ROOT / "traces"
_OUTPUT_DIR = _ROOT / "output"
_SERVER_SCRIPT = _ROOT / "server" / "mcp_server.py"


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run_crew(question: str) -> str:
    """Run the full Researcher → Writer → Verifier crew on a question.

    Args:
        question: The business question to answer.

    Returns:
        The final string output from the Verifier (verification report).

    Raises:
        RuntimeError: If the MCP server subprocess fails to start.
    """
    if not question or not question.strip():
        raise ValueError("question must not be empty")

    # MCP server parameters — runs the server as a subprocess over stdio
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(_SERVER_SCRIPT)],
        env=None,  # inherit parent env (picks up .env via dotenv)
    )

    with MCPServerAdapter(server_params) as mcp_tools:
        # Split tools by name for clean assignment
        tool_map = {t.name: t for t in mcp_tools}

        researcher_tools = [
            tool_map[n]
            for n in ("search_documents", "read_record")
            if n in tool_map
        ]
        writer_tools = [
            tool_map[n]
            for n in ("save_report",)
            if n in tool_map
        ]
        verifier_tools = [
            tool_map[n]
            for n in ("search_documents", "read_record")
            if n in tool_map
        ]

        # Build agents
        researcher = make_researcher(researcher_tools)
        writer = make_writer(writer_tools)
        verifier = make_verifier(verifier_tools)

        # Build tasks (chained context)
        research_task = make_research_task(question, researcher)
        write_task = make_write_task(question, writer, context_tasks=[research_task])
        verify_task = make_verify_task(question, verifier, context_tasks=[write_task])

        # Set output log path in traces/
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _TRACES_DIR.mkdir(parents=True, exist_ok=True)
        log_path = _TRACES_DIR / f"crew_run_{timestamp}.log"

        # Assemble crew
        crew = Crew(
            agents=[researcher, writer, verifier],
            tasks=[research_task, write_task, verify_task],
            process=Process.sequential,
            verbose=True,
            output_log_file=str(log_path),
        )

        result = crew.kickoff()

        # ------------------------------------------------------------------
        # Fallback: if the Writer agent did not actually call save_report
        # (common with local models that embed tool calls as text instead
        # of executing them), persist the report from the task output.
        # ------------------------------------------------------------------
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        md_files = list(_OUTPUT_DIR.glob("*.md"))
        if not md_files:
            writer_output = str(write_task.output) if write_task.output else ""
            if writer_output.strip():
                from server.mcp_server import save_report as _save_report

                # Try to extract a clean title from the output
                title = "crew_report"
                for line in writer_output.splitlines():
                    stripped = line.strip().lstrip("#").strip()
                    if stripped:
                        title = stripped[:80]
                        break
                _save_report(title=title, content=writer_output)

    # Persist trace
    _save_trace(question, str(result))

    return str(result)


# ---------------------------------------------------------------------------
# Trace helper
# ---------------------------------------------------------------------------

def _save_trace(question: str, result: str) -> None:
    """Save question + result to traces/ as a timestamped JSON file."""
    _TRACES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_path = _TRACES_DIR / f"trace_{timestamp}.json"
    trace_data = {
        "timestamp": timestamp,
        "question": question,
        "result": result,
    }
    trace_path.write_text(
        json.dumps(trace_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n[trace saved -> {trace_path}]")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="IT HelpDesk Assistant — Multi-Agent Crew",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m crew.crew
  python -m crew.crew --question "What is the SLA for P1 tickets?"
  python -m crew.crew --question "What should I do when ransomware is detected?"
        """,
    )
    parser.add_argument(
        "--question",
        "-q",
        type=str,
        default=None,
        help="Business question to answer. If omitted, you will be prompted.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Load .env if present
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    args = _parse_args()

    if args.question:
        question = args.question.strip()
    else:
        print("IT HelpDesk Assistant")
        print("=" * 40)
        question = input("Enter your question: ").strip()
        if not question:
            print("Error: question cannot be empty.")
            sys.exit(1)

    print(f"\nRunning crew for: {question!r}\n")
    final_output = run_crew(question)
    print("\n" + "=" * 60)
    print("FINAL OUTPUT")
    print("=" * 60)
    print(final_output)

    # Force-exit to kill the MCP server subprocess which can hang on Windows
    # when the stdio connection is not cleanly closed by MCPServerAdapter.
    os._exit(0)
