"""
tasks.py — CrewAI Task Definitions
=====================================
Three tasks, one per agent. Each task receives the agent it belongs to
and, where needed, a context list of upstream tasks whose output is
forwarded as input.

Tasks:
    make_research_task(question, agent)             → Task
    make_write_task(agent, context_tasks)           → Task
    make_verify_task(agent, context_tasks)          → Task
"""

from __future__ import annotations

from crewai import Task


def make_research_task(question: str, agent) -> Task:
    """Instruct the Researcher to retrieve all relevant evidence.

    Args:
        question:  The business question posed by the user.
        agent:     The Researcher Agent instance.

    Returns:
        A CrewAI Task that produces a structured evidence summary.
    """
    return Task(
        description=(
            f"Answer the following business question using the available tools:\n\n"
            f"QUESTION: {question}\n\n"
            "Steps to follow:\n"
            "1. Use search_documents to find the top-3 most relevant policy or "
            "runbook documents. Use multiple queries if needed.\n"
            "2. For any specific ticket IDs mentioned in documents or in your "
            "search results, use read_record to retrieve full ticket details.\n"
            "3. Compile all findings into a structured evidence summary.\n\n"
            "Output format:\n"
            "## Evidence Summary\n"
            "### Documents Found\n"
            "- [filename]: <key facts quoted verbatim with page/section reference>\n"
            "### Tickets Found\n"
            "- [TICK-NNN]: <status, priority, description, resolution notes>\n"
            "### Gaps\n"
            "- List anything the question asks for that you could not find evidence of.\n\n"
            "IMPORTANT: Do not infer or invent. Only report what the tools returned."
        ),
        expected_output=(
            "A structured evidence summary in markdown with clearly attributed "
            "quotes from documents and ticket data. All sources named explicitly."
        ),
        agent=agent,
    )


def make_write_task(agent, context_tasks: list[Task]) -> Task:
    """Instruct the Writer to produce a sourced report from Researcher output.

    Args:
        agent:          The Writer Agent instance.
        context_tasks:  List containing the research Task (provides context).

    Returns:
        A CrewAI Task that produces a markdown report saved to output/.
    """
    return Task(
        description=(
            "You have received an evidence summary from the Researcher. "
            "Write a clear, structured markdown report that directly answers "
            "the original question.\n\n"
            "Report structure:\n"
            "# Report: <question in title case>\n"
            "## Summary\n"
            "One paragraph directly answering the question.\n"
            "## Evidence\n"
            "Detailed findings with inline citations after every fact, "
            "e.g. 'P1 tickets must be resolved within 4 hours [sla_policy.txt]' "
            "or 'TICK-021 status is Open [TICK-021]'.\n"
            "## Recommendations\n"
            "Actionable next steps (only if evidence supports them).\n"
            "## Sources\n"
            "Bulleted list of all documents and ticket IDs referenced.\n\n"
            "After writing the report, call save_report to persist it. "
            "Provide the report title (e.g., 'IT SLA Report') and the full content as arguments.\n\n"
            "IMPORTANT: Do not include any fact not present in the evidence summary."
        ),
        expected_output=(
            "A complete markdown report saved to output/report.md. "
            "Every factual statement has an inline citation. "
            "The Sources section lists all referenced documents and tickets."
        ),
        agent=agent,
        context=context_tasks,
    )


def make_verify_task(agent, context_tasks: list[Task]) -> Task:
    """Instruct the Verifier to audit the Writer's report claim by claim.

    Args:
        agent:          The Verifier Agent instance.
        context_tasks:  List containing the write Task (provides context).

    Returns:
        A CrewAI Task that produces a verification verdict.
    """
    return Task(
        description=(
            "You have received the final report from the Writer. "
            "Your job is to verify every factual claim against the original sources.\n\n"
            "Steps:\n"
            "1. Read through the report carefully.\n"
            "2. For each claim that cites a document, use search_documents to "
            "retrieve that document and confirm the claim matches the source text.\n"
            "3. For each claim that cites a ticket ID, use read_record to retrieve "
            "the ticket and confirm the claim matches the ticket fields.\n"
            "4. Mark each claim as:\n"
            "   - VERIFIED — the source text supports the claim exactly\n"
            "   - FLAG — the source does not support the claim, the claim is "
            "exaggerated, or the citation is missing\n\n"
            "Output format:\n"
            "## Verification Report\n"
            "### Claim-by-Claim Audit\n"
            "| Claim | Source | Verdict | Notes |\n"
            "|---|---|---|---|\n"
            "| <quote> | <filename or TICK-NNN> | VERIFIED / FLAG | <reason> |\n\n"
            "### Overall Verdict\n"
            "PASS — all claims verified\n"
            "OR\n"
            "FAIL — N claims flagged (list them)\n\n"
            "IMPORTANT: If you cannot retrieve a cited source, mark the claim as FLAG."
        ),
        expected_output=(
            "A verification report in markdown table format. "
            "Every claim is audited with a VERIFIED or FLAG verdict. "
            "An overall PASS or FAIL verdict is given at the end."
        ),
        agent=agent,
        context=context_tasks,
    )
