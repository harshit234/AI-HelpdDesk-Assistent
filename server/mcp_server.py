"""
MCP Server — IT HelpDesk Assistant
===================================
Exposes three tools over stdio transport using FastMCP:

    search_documents(query, top_k)  — TF-IDF search over data/docs/*.txt
    read_record(ticket_id)          — Look up a ticket row from tickets.csv
    save_report(content, filename)  — Write a markdown report to output/

Run standalone:
    python server/mcp_server.py

Inspect with MCP Inspector:
    npx @modelcontextprotocol/inspector python server/mcp_server.py
"""

from __future__ import annotations

import csv
import math
import os
import re
import string
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Paths — resolved relative to this file so the server works from any cwd
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent.parent
_DOCS_DIR = _ROOT / "data" / "docs"
_TICKETS_CSV = _ROOT / "data" / "tickets.csv"
_OUTPUT_DIR = _ROOT / "output"

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP("IT HelpDesk Assistant")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Lower-case, strip punctuation, split on whitespace."""
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    return text.split()


def _tf(tokens: list[str]) -> dict[str, float]:
    """Term frequency for a token list."""
    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    total = len(tokens) or 1
    return {t: c / total for t, c in freq.items()}


def _cosine(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Cosine similarity between two TF dicts."""
    dot = sum(vec_a.get(t, 0.0) * vec_b.get(t, 0.0) for t in vec_b)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values())) or 1e-9
    mag_b = math.sqrt(sum(v * v for v in vec_b.values())) or 1e-9
    return dot / (mag_a * mag_b)


def _load_docs() -> list[dict[str, str]]:
    """Load all .txt files from data/docs/. Returns list of {filename, text}."""
    docs = []
    for p in sorted(_DOCS_DIR.glob("*.txt")):
        docs.append({"filename": p.name, "text": p.read_text(encoding="utf-8")})
    return docs


def _snippet(text: str, query_tokens: list[str], max_chars: int = 300) -> str:
    """Return the 300-char window around the first query-token match."""
    text_lower = text.lower()
    best_pos = len(text)
    for token in query_tokens:
        idx = text_lower.find(token)
        if 0 <= idx < best_pos:
            best_pos = idx
    start = max(0, best_pos - 50)
    return text[start : start + max_chars].strip()


def _read_tickets() -> list[dict[str, str]]:
    """Parse tickets.csv and return list of row dicts."""
    rows = []
    with open(_TICKETS_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if any(v.strip() for v in row.values()):  # skip blank lines
                rows.append(dict(row))
    return rows


# ---------------------------------------------------------------------------
# Resource — docs://index
# ---------------------------------------------------------------------------

@mcp.resource("docs://index")
def list_documents() -> str:
    """Return a JSON list of all available policy/runbook document filenames.

    Agents should read this resource first to discover which documents
    exist before calling search_documents.

    Returns:
        A JSON string containing a list of .txt filenames available in data/docs/.
    """
    import json

    filenames = sorted(p.name for p in _DOCS_DIR.glob("*.txt"))
    if not filenames:
        return json.dumps({"error": f"No documents found in {_DOCS_DIR}"})
    return json.dumps({"documents": filenames, "count": len(filenames)}, indent=2)


# ---------------------------------------------------------------------------
# Tool 1 — search_documents
# ---------------------------------------------------------------------------

@mcp.tool()
def search_documents(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Search policy and runbook documents using TF-IDF cosine similarity.

    Args:
        query:  Natural-language question or keywords to search for.
        top_k:  Number of top-matching documents to return (default 3, max 12).

    Returns:
        A list of dicts, each with:
            filename — name of the .txt file
            score    — cosine similarity score (0.0–1.0)
            snippet  — up to 300 chars from the most relevant part of the doc
    """
    if not query or not query.strip():
        return [{"error": "query must not be empty"}]

    if len(query) > 500:
        return [{"error": "query must not exceed 500 characters"}]

    top_k = max(1, min(int(top_k), 12))
    query_tokens = _tokenize(query)
    query_tf = _tf(query_tokens)

    docs = _load_docs()
    if not docs:
        return [{"error": f"No documents found in {_DOCS_DIR}"}]

    scored = []
    for doc in docs:
        doc_tf = _tf(_tokenize(doc["text"]))
        score = _cosine(query_tf, doc_tf)
        if score > 0.0:
            scored.append(
                {
                    "filename": doc["filename"],
                    "score": round(score, 4),
                    "snippet": _snippet(doc["text"], query_tokens),
                }
            )

    if not scored:
        return [{"message": "No matching documents found."}]

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ---------------------------------------------------------------------------
# Tool 2 — read_record
# ---------------------------------------------------------------------------

_TICKET_ID_RE = re.compile(r"^TICK-\d{3,}$", re.IGNORECASE)


@mcp.tool()
def read_record(id: str) -> dict[str, Any]:
    """Look up a helpdesk ticket by its ID.

    Args:
        id: The ticket identifier, e.g. "TICK-001". Case-insensitive.

    Returns:
        A dict with all ticket fields, or an error dict if not found.
    """
    if not id or not id.strip():
        return {"error": "id must not be empty"}

    id_clean = id.strip().upper()
    if not _TICKET_ID_RE.match(id_clean):
        return {
            "error": f"Invalid ticket ID format '{id_clean}'. Expected format: TICK-NNN"
        }

    try:
        rows = _read_tickets()
    except Exception as e:
        return {"error": f"Failed to read ticket database: {str(e)}"}

    if not rows:
        return {"error": "No ticket records found in database."}

    for row in rows:
        if row.get("ticket_id", "").upper() == id_clean:
            return row

    return {"error": f"Ticket '{id_clean}' not found in records"}


# ---------------------------------------------------------------------------
# Tool 3 — save_report
# ---------------------------------------------------------------------------

@mcp.tool()
def save_report(title: str, content: str) -> str:
    """Write a sourced markdown report to the output/ directory.

    Args:
        title:    The title of the report (used to derive the filename).
        content:  Full markdown content of the report.

    Returns:
        Absolute path to the saved file as a string.
    """
    if not title or not title.strip():
        return "Error: title must not be empty"
    if not content or not content.strip():
        return "Error: content must not be empty"

    # Derive filename from title: lowercase, replace spaces/special chars with underscores, collapse underscores
    slug = re.sub(r"[^\w\-_]+", "_", title.strip().lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    if not slug:
        slug = "report"
    filename = f"{slug}.md"

    # Ensure output directory exists
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _OUTPUT_DIR / filename
    
    try:
        out_path.write_text(content, encoding="utf-8")
    except Exception as e:
        return f"Error: Failed to write file: {str(e)}"
        
    return str(out_path.resolve())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
