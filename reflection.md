# Reflection

*Write this after your demo is complete. Suggested prompts below — delete and replace with your own words.*

---

## What went well

- The clean separation of `server/`, `crew/`, and `tests/` made it easy to develop and test each layer independently. Tool functions could be imported and called without starting the MCP server.
- The `MCPServerAdapter` as a context manager ensured the subprocess was always properly closed — no zombie processes during development.
- TF-IDF search was fast to implement and worked well for the narrow IT-ops vocabulary.

---

## What was hard

- <!-- e.g. Getting the CrewAI context chaining right between tasks took iteration -->
- <!-- e.g. Debugging the MCPServerAdapter connection required the MCP Inspector -->
- <!-- e.g. Prompt engineering the Verifier to actually re-retrieve evidence, not just echo the Writer -->

---

## What I would do differently

- <!-- e.g. Use sentence-transformers for semantic search if the corpus grew beyond ~50 documents -->
- <!-- e.g. Add a streaming output mode so long crew runs show progress in real time -->
- <!-- e.g. Store traces in SQLite for easier querying -->

---

## What I learned

- <!-- e.g. The MCP protocol separates tool definition from transport cleanly — the same tools work over stdio, HTTP, or direct import -->
- <!-- e.g. CrewAI's `context` parameter on Task is the key to passing structured output between agents -->
- <!-- e.g. Keeping agents narrow (no delegation) produced more predictable outputs than general-purpose agents -->

---

## If I had one more day

- <!-- e.g. Add a Streamlit UI so non-technical users can ask questions via a browser -->
- <!-- e.g. Pre-compute TF-IDF vectors at startup to speed up repeated searches -->
- <!-- e.g. Add the three pre-tested example questions to a demo script with expected output -->
