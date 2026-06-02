# Decision Log

This file records the key design decisions made during development and the reasoning behind them.

---

## Decision 1 — TF-IDF over a vector DB for document search

**Date:** 2025-01-xx  
**Decision:** Use scikit-learn TF-IDF cosine similarity instead of a vector database (Chroma, FAISS, Pinecone).

**Reasoning:**
- The corpus is small and fixed (12 documents, ~30 KB total). A vector DB adds significant complexity and operational overhead for no measurable benefit at this scale.
- TF-IDF cosine similarity is fully deterministic and reproducible — no embedding model version drift.
- Zero extra infrastructure: no server to start, no index to persist.
- Interviews value clean, justified trade-offs over unnecessary complexity.

**Trade-off:** Semantic similarity (e.g. "outage" matching "downtime") is weaker than embeddings. Mitigated by the narrow, domain-specific vocabulary of IT operations documents.

---

## Decision 2 — FastMCP (stdio transport) over HTTP/SSE

**Date:** 2025-01-xx  
**Decision:** Use `stdio` transport for the MCP server, not HTTP/SSE.

**Reasoning:**
- `stdio` is the standard transport for local MCP servers used by the CrewAI `MCPServerAdapter`.
- No port management, firewall rules, or authentication tokens needed.
- The `MCPServerAdapter` manages subprocess lifecycle automatically.

**Trade-off:** stdio does not support remote clients. Acceptable for this local-only use case.

---

## Decision 3 — Agents and tasks as factory functions, not module-level globals

**Date:** 2025-01-xx  
**Decision:** `make_researcher()`, `make_writer()`, `make_verifier()` return new instances each call.

**Reasoning:**
- Tools (MCP tool wrappers) must be injected at runtime — they are only available inside the `MCPServerAdapter` context manager.
- Factory functions make testing straightforward: pass mock tools in tests without patching globals.
- Avoids subtle shared-state bugs in long-running processes.

---

## Decision 4 — Ollama/Mistral as default LLM

**Date:** 2025-01-xx  
**Decision:** Default to Ollama with the `mistral` model; OpenAI and Gemini are opt-in via `.env`.

**Reasoning:**
- Free, local, no API key needed — lowers barrier for reviewers to run the project.
- CrewAI's `LLM` class supports both OpenAI-compatible endpoints (Ollama) and native Gemini, switchable by changing three env vars.

---

## Decision 5 — Verifier uses the same MCP tools as Researcher

**Date:** 2025-01-xx  
**Decision:** The Verifier agent receives `search_documents` and `read_record` — it re-retrieves evidence independently.

**Reasoning:**
- The Verifier should not trust the Researcher's cached output — it must re-check each claim against the source.
- This is the definition of a proper verification step: independent retrieval, not just re-reading the prior agent's text.
