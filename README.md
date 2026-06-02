# IT HelpDesk Assistant — MCP + CrewAI Multi-Agent System

A multi-agent operations assistant that answers business questions by searching internal policy documents and helpdesk records. Built with a FastMCP server exposing tools over local data, and a CrewAI crew of three agents that retrieve evidence and write sourced reports.
---

## What it does

You ask a business question. The crew:
1. **Researcher** — searches policy documents and reads ticket records using MCP tools
2. **Writer** — synthesises findings into a structured markdown report with citations
3. **Verifier** — checks every claim in the report against the retrieved evidence and flags anything unsupported

Every fact in the output names the document or ticket it came from. If no evidence is found, the agent says so — it does not invent an answer.

---

## Architecture

```
data/docs/*.txt  ──►  MCP Server (FastMCP / stdio)  ──►  CrewAI Crew
data/tickets.csv ──►   search_documents()            ──►   Researcher agent
                        read_record()                ──►   Writer agent
                        save_report()                ──►   Verifier agent
                             │                                   │
                             └─────────────────────────────► output/report.md
```

The MCP server runs as a subprocess. The crew connects to it via `MCPServerAdapter` over stdio.

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11 or 3.12 |
| pip | latest |
| Ollama (Option A) | latest — [install](https://ollama.com) |
| Node.js (for MCP Inspector) | 18+ |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/ops-assistant.git
cd ops-assistant
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

Open `.env` and choose your model:

**Option A — Ollama (local, free, recommended)**
```bash
# Pull a model first
ollama pull mistral

# .env values (already set in .env.example)
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_MODEL_NAME=ollama/mistral
OPENAI_API_KEY=ollama
```

**Option B — Gemini**
```bash
# Uncomment and fill in .env
GEMINI_API_KEY=your_key_here
```

---

## Running the MCP server

Start the server standalone to test it:

```bash
python server/mcp_server.py
```

Test it in the MCP Inspector (in a separate terminal):

```bash
npx @modelcontextprotocol/inspector python server/mcp_server.py
```

Open `http://localhost:5173` in your browser. You should see three tools listed:
- `search_documents` — searches policy documents by query string
- `read_record` — looks up a ticket by ID from tickets.csv
- `save_report` — writes a sourced markdown report to `output/`

Try calling each tool manually in the Inspector before running the crew.

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

**`tests/test_tools.py`** — calls MCP tool functions directly (no server needed):
- valid inputs return expected structure
- empty inputs return a clear error message
- non-existent record IDs return "not found" message
- malformed ticket IDs return a validation error

**`tests/test_crew.py`** — end-to-end test on a fixed question:
- verifies a report file is created in `output/`
- verifies the report contains at least one citation (document filename)
- verifies no exception is raised

---

## Project structure

```
ops-assistant/
├── server/
│   ├── mcp_server.py        # FastMCP server — 3 tools, validated inputs
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
│   ├── test_tools.py        # Unit tests — MCP tools called directly
│   └── test_crew.py         # E2E test — crew on fixed question
├── output/                  # Generated reports (gitignored)
├── traces/                  # Agent run logs (gitignored)
├── demo/                    # Demo recording
├── .env.example             # Environment variable template
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

---

## Safety notes

- The MCP server runs as a local subprocess over stdio. Only connect to servers you trust.
- All tool inputs are validated with strict schemas before any file I/O.
- `max_iter` is set on every agent to prevent runaway loops.
- The `MCPServerAdapter` is always used as a context manager so the subprocess is properly closed.
- No secrets, API keys, or private data are committed. Use `.env` for all credentials.

---

## References

- [Model Context Protocol](https://modelcontextprotocol.io/docs/getting-started/intro)
- [FastMCP (MCP Python SDK)](https://github.com/modelcontextprotocol/python-sdk)
- [Build an MCP server step by step](https://gofastmcp.com/tutorials/create-mcp-server)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [CrewAI docs](https://docs.crewai.com)
- [CrewAI + MCP integration](https://docs.crewai.com/en/mcp/overview)
