# IT HelpDesk Assistant — MCP + CrewAI Multi-Agent System

A multi-agent operations assistant that answers business questions by searching internal policy documents and helpdesk records. Built with a FastMCP server exposing tools and resources over local data, and a CrewAI crew of three agents that retrieve evidence and write sourced reports.

---

## 🎬 Demo

▶️ [Watch the demo on Google Drive](https://drive.google.com/file/d/1u0-NiUX55RpiK-gDUBuYTWnYAX2QED6p/view?usp=sharing)

---

## What it does

You ask a business question. The crew:
1. **Researcher** — reads the resource document to discover available documents, searches policy documents and reads ticket records using MCP tools
2. **Writer** — synthesises findings into a structured markdown report with citations, saved via `save_report`
3. **Verifier** — checks every claim in the report against the retrieved evidence and flags anything unsupported

Every fact in the output names the document or ticket it came from. If no evidence is found, the agent says so — it does not invent an answer.

---

## Architecture

```
data/docs/*.txt  ──►  MCP Server (FastMCP / stdio)  ──►  CrewAI Crew
data/tickets.csv ──►   docs://index   (resource)    ──►   Researcher agent
                         search_documents()          ──►   Writer agent
                         read_record()               ──►   Verifier agent
                         save_report()                           │
                              │                                  │
                              └──────────────────────────► output/<slug>.md
```

The MCP server runs as a subprocess. The crew connects to it via `MCPServerAdapter` over stdio.

---

## MCP Server — Tools & Resource

### Resource

| URI | Description |
|---|---|
| `docs://index` | Returns a JSON list of all 12 available policy document filenames. Read this first before searching. |

### Tools

| Tool | Signature | Description |
|---|---|---|
| `search_documents` | `(query: str, top_k: int = 3)` | TF-IDF cosine similarity search over `data/docs/*.txt`. Returns filename, score, and snippet. |
| `read_record` | `(id: str)` | Lookup a helpdesk ticket by ID (e.g. `TICK-001`). Validates format before file I/O. |
| `save_report` | `(title: str, content: str)` | Writes a markdown report to `output/`. Filename derived from title slug (e.g. `"IT SLA Report"` → `it_sla_report.md`). |

#### Input Validation (all tools)
- `search_documents`: query must be non-empty and ≤ 500 characters
- `read_record`: ID must match `TICK-NNN` pattern; returns structured error if not found
- `save_report`: both title and content must be non-empty; returns structured error otherwise
- **Zero stack traces** — all error cases return human-readable JSON messages

---

## Prerequisites

| Requirement | Version | Status |
|---|---|---|
| Python | 3.11 or 3.12  | — |
| pip | latest | — |
| Ollama | latest — [install](https://ollama.com) |
| Node.js (for MCP Inspector)|

> ⚠️ **Python 3.14 Note:** The CrewAI integration tests (`test_crew.py`) are automatically skipped on Python 3.14+ due to an upstream incompatibility between Pydantic V1 and Python 3.14 (via `chromadb`). The MCP server tools (`test_tools.py`) work fully on all Python versions.

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/harshit234/AI-HelpdDesk-Assistent.git
cd AI-HelpdDesk-Assistent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Your `.env` is already pre-configured for Ollama:

```ini
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_MODEL_NAME=ollama/mistral
OPENAI_API_KEY=ollama
```

### 5. Pull the Ollama model & start Ollama

Ollama is already installed. Pull the model and make sure it's running:

```bash
ollama pull mistral
ollama serve
```

Verify the model is available:
```bash
ollama list
# mistral:latest    6577803aa9a0    4.4 GB    ...
```

---

## Running the MCP server

Start the server standalone to test it:

```bash
python server/mcp_server.py
```

### Test in the MCP Inspector

```bash
npx @modelcontextprotocol/inspector python server/mcp_server.py
```

Open `http://localhost:5173` in your browser. You should see:

**Resources:**
- `docs://index` — lists all 12 policy document filenames

**Tools:**
- `search_documents` — TF-IDF search over policy documents
- `read_record` — looks up a ticket by ID from tickets.csv
- `save_report` — writes a sourced markdown report to `output/`

#### Inspector test results (verified)

| Tool | Input | Response |
|---|---|---|
| `search_documents` | `query="SLA"` | Matching docs with scores and snippets |
| `search_documents` | `query=""` | `{"error": "query must not be empty"}` |
| `search_documents` | `query="nonexistent"` | `{"message": "No matching documents found."}` |
| `search_documents` | 501 char query | `{"error": "query must not exceed 500 characters"}` |
| `read_record` | `id="TICK-001"` | Full ticket dict |
| `read_record` | `id=""` | `{"error": "id must not be empty"}` |
| `read_record` | `id="TICK-999"` | `{"error": "Ticket 'TICK-999' not found in records"}` |
| `read_record` | `id="ABC-123"` | `{"error": "Invalid ticket ID format..."}` |
| `save_report` | `title="Test Report"` + content | Returns absolute path to saved `.md` |
| `save_report` | `title=""` | Error: title must not be empty` |
| `save_report` | `content=""` | Error: content must not be empty` |

---

## Running the crew

```bash
python crew/crew.py
```

The crew will prompt you for a business question, or you can pass one directly:

```bash
python crew/crew.py --question "What is the SLA for P1 tickets and how many P1 tickets are currently open?"
```

The final report is saved to `output/` and the run trace is saved to `traces/`.

---

## Example questions

These three questions are pre-tested with saved outputs in `traces/`:

```
1. What is the SLA for P1 tickets, and how many P1 tickets are currently open?

2. What should be done when ransomware is detected on an endpoint,
   and is there an active ransomware incident right now?

3. What is the patching deadline for CVE-2025-0198 and what is
   the current status of the related ticket?
```

---

## Running tests

```bash
pytest tests/ -v
```

**Current test status:**
```
======================== 27 passed, 6 skipped in 3.79s ========================
```

- **27 passed** — `tests/test_tools.py` unit tests for all 3 MCP tools
- **6 skipped** — `tests/test_crew.py` integration tests (skipped on Python 3.14+ automatically)

**`tests/test_tools.py`** — calls MCP tool functions directly (no server needed):
- `TestSearchDocuments` (11 tests): valid queries, top-k, empty/whitespace/too-long queries, no-match case
- `TestReadRecord` (9 tests): valid IDs, case-insensitive lookup, nonexistent, malformed, missing file
- `TestSaveReport` (7 tests): valid title/content, slugification, empty title, empty content

**`tests/test_crew.py`** — end-to-end test on a fixed question (requires Python ≤ 3.13 + Ollama running)

---

## Project structure

```
AI-HelpdDesk-Assistent/
├── server/
│   ├── mcp_server.py        # FastMCP server — 3 tools + docs://index resource
│   └── __init__.py
├── crew/
│   ├── agents.py            # Researcher, Writer, Verifier — roles and tools
│   ├── tasks.py             # Task definitions with expected outputs
│   ├── crew.py              # Crew assembly, MCPServerAdapter, runner
│   └── __init__.py
├── data/
│   ├── docs/                # 12 policy and runbook .txt files
│   └── tickets.csv          # 35 IT helpdesk tickets
├── tests/
│   ├── test_tools.py        # Unit tests — 27 passing
│   └── test_crew.py         # E2E test — auto-skipped on Python 3.14+
├── output/                  # Generated reports (gitignored, .gitkeep present)
├── traces/                  # Agent run logs (gitignored, .gitkeep present)
├── demo/                    # Demo recording
├── .env.example             # Environment variable template (Ollama pre-configured)
├── .gitignore
├── requirements.txt
├── decision_log.md          # Design decisions and trade-offs
├── reflection.md            # Post-build reflection
└── ai_usage_log.md          # AI assistance log
```

---

## Data

### Policy documents (`data/docs/`)

| File | Contents |
|---|---|
| `sla_policy.txt` | P1–P4 response and resolution times, breach rules |
| `escalation_procedure.txt` | Tier 1/2/3 teams, named engineers, steps |
| `runbook_database_outage.txt` | DB recovery steps, RTO/RPO, failover |
| `runbook_network_incident.txt` | VPN, DNS, ISP, load balancer failures |
| `change_management_policy.txt` | Standard/Normal/Emergency changes, CAB |
| `security_incident_policy.txt` | Containment, CERT-In notification, ransomware |
| `server_health_monitoring_policy.txt` | Alert thresholds, PagerDuty, on-call schedule |
| `access_management_policy.txt` | Account provisioning, MFA, revocation |
| `backup_recovery_policy.txt` | Backup schedules, retention, RTO/RPO |
| `patch_management_policy.txt` | CVSS-based timelines, testing requirements |
| `vendor_management_policy.txt` | ISP contacts, circuit IDs, insurance |
| `oncall_policy.txt` | On-call rules, rotation, compensation |

### Tickets (`data/tickets.csv`)

35 rows with columns: `ticket_id`, `created_date`, `category`, `status`, `priority`, `assigned_to`, `assigned_group`, `description`, `resolution_notes`.

Covers: database outages, network incidents, security events, patch management, access requests, vendor issues, change requests — spanning P1 through P4.

## Safety & Security

- **Indirect Prompt Injection Protection (RAG Defense):**
  - **Tool-Level Scanner:** The `search_documents` tool dynamically scans matched documents for known injection keywords (e.g., "ignore all previous instructions", "system override"). If a threat is detected, it logs a stderr warning `[SECURITY WARNING]`, flags the metadata, and prepends a clear security warning header to the document snippet before it reaches the agent.
  - **Agent Prompt Hardening:** Researcher, Writer, and Verifier agent goal and backstory prompts have been hardened to treat external documents as untrusted data, prioritize system prompt instructions, and ignore any embedded overrides or system instructions.
- **Input Validation:** All tool inputs are validated with strict schemas before any file I/O (e.g., query length, ticket ID pattern checking). No Python stack traces are leaked on invalid inputs.
- **Agent Limits:** `max_iter` is set to `8` on every agent to prevent runaway loops. Agent delegation is disabled (`allow_delegation=False`) to keep the pipeline sequential and predictable.
- **Subprocess Isolation:** The MCP server runs as a local subprocess over stdio. The `MCPServerAdapter` is used as a context manager to ensure proper process lifecycle management and cleanup.
- **Environment Secrets:** No secrets, API keys, or private data are committed. `.env` is gitignored.

---

## References

- [Model Context Protocol](https://modelcontextprotocol.io/docs/getting-started/intro)
- [FastMCP (MCP Python SDK)](https://github.com/modelcontextprotocol/python-sdk)
- [Build an MCP server step by step](https://gofastmcp.com/tutorials/create-mcp-server)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [CrewAI docs](https://docs.crewai.com)
- [CrewAI + MCP integration](https://docs.crewai.com/en/mcp/overview)
- [Ollama](https://ollama.com)
