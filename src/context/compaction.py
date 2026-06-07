"""
Compaction strategies and prompt templates for workspace report synthesis.

Each strategy controls how aggressively the workspace report is compressed
at each update step.
"""

from enum import Enum


class CompactionStrategy(Enum):
    """Compression aggressiveness for workspace report synthesis.

    - AGGRESSIVE:  Keep only key findings and essential context.  Highest
                   token savings but may lose peripheral details.
    - BALANCED:    Retain moderately detailed context while compressing.
                   Default trade-off between completeness and size.
    - VERBOSE:     Minimally compress; preserve more of the original context
                   for tasks where detail is critical.
    """

    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    VERBOSE = "verbose"


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
# Each template receives these format arguments:
#   {current_report}    – the current state of report_text
#   {new_observations}  – raw observations from the latest step
#   {action_outcome}    – outcome of the action taken
#   {key_findings}      – bullet-list of existing key findings
#   {step_count}        – number of update cycles so far

COMPACTION_PROMPTS: dict[CompactionStrategy, str] = {
    CompactionStrategy.AGGRESSIVE: (
        "You are a workspace compression agent.\n"
        "You have a current workspace report and new information from the latest step.\n"
        "Produce a **new** workspace report that is maximally compressed.\n\n"
        "## Current Report\n{current_report}\n\n"
        "## New Observations\n{new_observations}\n\n"
        "## Action Outcome\n{action_outcome}\n\n"
        "## Existing Key Findings\n{key_findings}\n\n"
        "## Instructions (AGGRESSIVE)\n"
        "- Keep ONLY the most critical facts and decisions.\n"
        "- Discard all peripheral details, partial results, and redundant observations.\n"
        "- Output a single concise paragraph plus a short bullet list of key findings.\n"
        "  Aim for under 200 words.\n"
        "- Format as:\n"
        "  WORKSPACE_REPORT:\n"
        "  <condensed report>\n"
        "  KEY_FINDINGS:\n"
        "  - <finding 1>\n"
        "  - <finding 2>"
    ),
    CompactionStrategy.BALANCED: (
        "You are a workspace compression agent.\n"
        "You have a current workspace report and new information from the latest step.\n"
        "Produce a **new** workspace report that is concise but retains important context.\n\n"
        "## Current Report\n{current_report}\n\n"
        "## New Observations\n{new_observations}\n\n"
        "## Action Outcome\n{action_outcome}\n\n"
        "## Existing Key Findings\n{key_findings}\n\n"
        "## Instructions (BALANCED)\n"
        "- Retain the essential narrative: what was done, what was found, what was decided.\n"
        "- Omit redundant or low-value details.\n"
        "- Output a short markdown section (2-4 paragraphs) plus key finding bullets.\n"
        "  Aim for under 500 words.\n"
        "- Keep the overall structure familiar so follow-up steps can orient quickly.\n"
        "- Format as:\n"
        "  WORKSPACE_REPORT:\n"
        "  <condensed report>\n"
        "  KEY_FINDINGS:\n"
        "  - <finding 1>\n"
        "  - <finding 2>"
    ),
    CompactionStrategy.VERBOSE: (
        "You are a workspace compression agent.\n"
        "You have a current workspace report and new information from the latest step.\n"
        "Produce a **new** workspace report that preserves as much detail as possible.\n\n"
        "## Current Report\n{current_report}\n\n"
        "## New Observations\n{new_observations}\n\n"
        "## Action Outcome\n{action_outcome}\n\n"
        "## Existing Key Findings\n{key_findings}\n\n"
        "## Instructions (VERBOSE)\n"
        "- Keep all meaningful context steps so far.\n"
        "- Only remove clear duplicates or off-topic content.\n"
        "- Maintain full paragraphs and chronological flow.\n"
        "- Output a markdown section of any length, followed by key findings.\n"
        "- Format as:\n"
        "  WORKSPACE_REPORT:\n"
        "  <detailed report>\n"
        "  KEY_FINDINGS:\n"
        "  - <finding 1>\n"
        "  - <finding 2>"
    ),
}
