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
            "you MUST use search_documents before providing any answer\n\n"
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
            "IMPORTANT: You MUST use the search_documents tool to search documents "
            "and read_record to retrieve ticket details. Do not answer from memory. "
            "Do not infer or invent. Only report what the tools returned. "
            "Specifically, you MUST use search_documents before providing any answer."
        ),
        expected_output=(
            "A structured markdown evidence summary containing '## Evidence Summary', "
            "'### Documents Found', '### Tickets Found', and '### Gaps' sections. "
            "It must only contain facts retrieved using the tools, with explicit filenames and ticket IDs cited. "
            "No fabricated or assumed information is allowed."
        ),
        agent=agent,
    )


def make_write_task(question: str, agent, context_tasks: list[Task]) -> Task:
    """Instruct the Writer to produce a sourced report from Researcher output.

    Args:
        question:       The original business question.
        agent:          The Writer Agent instance.
        context_tasks:  List containing the research Task (provides context).

    Returns:
        A CrewAI Task that produces a markdown report saved to output/.
    """
    return Task(
        description=(
            f"You have received an evidence summary from the Researcher for the original question:\n"
            f"QUESTION: {question}\n\n"
            "Write a clear, structured markdown report that directly answers this question.\n\n"
            "Report structure:\n"
            "# Report: <question in title case>\n"
            "## Summary\n"
            "One paragraph directly answering the question.\n"
            "## Evidence\n"
            "Detailed findings with inline citations after every fact.\n"
            "## Recommendations\n"
            "Actionable next steps (only if evidence supports them).\n"
            "## Sources\n"
            "Bulleted list of all documents and ticket IDs referenced.\n\n"
            "CITATION FORMAT (mandatory):\n"
            "Every factual statement derived from a retrieved document or ticket "
            "MUST include an inline citation in square brackets immediately after "
            "the fact. Use exactly these formats:\n"
            "- For documents: [filename.txt]  e.g. 'P1 must be resolved within "
            "4 hours [sla_policy.txt]'\n"
            "- For tickets:   [TICK-NNN]      e.g. 'TICK-021 status is Open "
            "[TICK-021]'\n"
            "Do NOT use other citation styles such as (Source: ...) or "
            "(ref: ...). Only the [filename.txt] and [TICK-NNN] formats are "
            "acceptable.\n\n"
            "You MUST call the save_report tool to persist the report. "
            "Do not simply return the report text. "
            "The task is considered complete only after save_report has been "
            "successfully called and has returned a confirmation containing "
            "the saved file path.\n\n"
            "Provide the report title (e.g., 'IT SLA Report') and the full "
            "markdown content as the two arguments to save_report. "
            "Your final answer MUST be the absolute file path returned by "
            "the save_report tool.\n\n"
            "IMPORTANT: Do not include any fact not present in the evidence summary."
        ),
        expected_output=(
            "A confirmation message from the save_report tool containing the "
            "absolute file path where the report was saved "
            "(e.g. 'C:/Users/.../output/it_sla_report.md')."
        ),
        agent=agent,
        context=context_tasks,
    )


def make_verify_task(question: str, agent, context_tasks: list[Task]) -> Task:
    """Instruct the Verifier to audit the Writer's report claim by claim.

    Args:
        question:       The original business question.
        agent:          The Verifier Agent instance.
        context_tasks:  List containing the write Task (provides context).

    Returns:
        A CrewAI Task that produces a verification verdict.
    """
    return Task(
        description=(
            "you MUST use search_documents before providing any answer\n\n"
            f"You have received the final report from the Writer for the original question:\n"
            f"QUESTION: {question}\n\n"
            "Your job is to verify every factual claim in the report against the original sources.\n\n"
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
            "TERMINOLOGY REQUIREMENT: When referring to service level agreements, "
            "response time commitments, or resolution time commitments, you MUST "
            "use the exact term 'SLA'. Do not replace it with synonyms such as "
            "'service commitment', 'response target', or 'support obligation'.\n\n"
            "IMPORTANT: If you cannot retrieve a cited source, mark the claim as FLAG. "
            "You MUST use the search_documents or read_record tool to retrieve the sources and verify each claim before providing any answer."
        ),
        expected_output=(
            "A verification report in markdown format that explicitly references "
            "the applicable SLA requirements. It must contain: 1) A '## Verification Report' header, "
            "2) A '### Claim-by-Claim Audit' section with a markdown table containing Claim, Source, Verdict, "
            "and Notes columns, auditing every single statement in the report, and 3) An '### Overall Verdict' "
            "concluding with either 'PASS — all claims verified' or 'FAIL — N claims flagged'. "
            "The term 'SLA' must appear at least once when discussing response or resolution commitments."
        ),
        agent=agent,
        context=context_tasks,
    )
