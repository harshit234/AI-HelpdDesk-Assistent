"""
agents.py — CrewAI Agent Definitions
======================================
Three agents with distinct roles, goals, and backstories.
Each agent function accepts a list of MCP-backed tools so that
tools can be injected at runtime (e.g. from MCPServerAdapter).

Agents:
    make_researcher(tools) → Agent
    make_writer(tools)     → Agent
    make_verifier(tools)   → Agent
"""

from __future__ import annotations

from crewai import Agent, LLM


def _llm() -> LLM:
    """Build the shared LLM from environment variables.

    Reads:
        OPENAI_API_BASE      — base URL (default: http://localhost:11434/v1)
        OPENAI_MODEL_NAME    — model name (default: ollama/mistral)
        OPENAI_API_KEY       — API key (default: ollama)
    """
    import os

    return LLM(
        model=os.getenv("OPENAI_MODEL_NAME", "ollama/mistral"),
        base_url=os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "ollama"),
        temperature=0.1,
    )


# ---------------------------------------------------------------------------
# Researcher
# ---------------------------------------------------------------------------

def make_researcher(tools: list) -> Agent:
    """Searches documents and reads ticket records. Never invents facts.

    Args:
        tools: List of MCP tool wrappers (search_documents, read_record).

    Returns:
        A configured CrewAI Agent instance.
    """
    return Agent(
        role="IT Operations Researcher",
        goal=(
            "Retrieve all evidence needed to answer the question accurately. "
            "Search policy documents and read ticket records. "
            "Return a structured evidence summary — never invent or infer facts."
        ),
        backstory=(
            "You are a meticulous IT operations analyst with deep knowledge of "
            "ITIL practices. You have access to the company's internal policy "
            "library and the full helpdesk ticket history. You only state facts "
            "that you can directly quote from a retrieved document or ticket. "
            "You always note the source filename or ticket ID for every fact."
        ),
        tools=tools,
        llm=_llm(),
        verbose=True,
        max_iter=8,
        allow_delegation=False,
    )


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def make_writer(tools: list) -> Agent:
    """Synthesises researcher findings into a structured markdown report.

    Args:
        tools: List of MCP tool wrappers (save_report).

    Returns:
        A configured CrewAI Agent instance.
    """
    return Agent(
        role="IT Operations Report Writer",
        goal=(
            "Produce a clear, structured markdown report that answers the "
            "question using only the evidence supplied by the Researcher. "
            "Every factual claim must include an inline citation "
            "(e.g. [sla_policy.txt] or [TICK-021]). "
            "Save the final report using the save_report tool."
        ),
        backstory=(
            "You are a senior technical writer who specialises in IT operations "
            "documentation. You never add information beyond what the Researcher "
            "has found. Your reports follow a consistent structure: Summary, "
            "Evidence, Recommendations, and Sources. You always cite the exact "
            "document or ticket ID that supports each claim."
        ),
        tools=tools,
        llm=_llm(),
        verbose=True,
        max_iter=5,
        allow_delegation=False,
    )


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

def make_verifier(tools: list) -> Agent:
    """Reads the final report and checks every claim against retrieved evidence.

    Args:
        tools: List of MCP tool wrappers (search_documents, read_record).

    Returns:
        A configured CrewAI Agent instance.
    """
    return Agent(
        role="IT Operations Fact Verifier",
        goal=(
            "Read the final report produced by the Writer. "
            "For every factual claim, retrieve the cited source and confirm "
            "the claim is accurate. "
            "Output a verification verdict: mark each claim as VERIFIED or FLAG. "
            "Flag any claim that is unsupported, exaggerated, or missing a citation."
        ),
        backstory=(
            "You are a rigorous quality assurance analyst. You do not trust "
            "anything written in a report unless you can verify it against the "
            "original source document or ticket. You use the same search and "
            "lookup tools as the Researcher to re-check every piece of evidence. "
            "You are the last line of defence against hallucination."
        ),
        tools=tools,
        llm=_llm(),
        verbose=True,
        max_iter=8,
        allow_delegation=False,
    )
