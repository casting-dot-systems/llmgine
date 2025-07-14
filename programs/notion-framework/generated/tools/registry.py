"""Tool registry for all generated Notion tools."""

from typing import List
from llmgine.llm.tools import Tool

from .events_projects_tools import TOOLS as EVENTSPROJECTS_TOOLS
from .meetings_and_tasks_tools import TOOLS as MEETINGSANDTASKS_TOOLS
from .teams_tools import TOOLS as TEAMS_TOOLS
from .documents_tools import TOOLS as DOCUMENTS_TOOLS

# All generated tools
ALL_TOOLS: List[Tool] = []

ALL_TOOLS.extend(EVENTSPROJECTS_TOOLS)
ALL_TOOLS.extend(MEETINGSANDTASKS_TOOLS)
ALL_TOOLS.extend(TEAMS_TOOLS)
ALL_TOOLS.extend(DOCUMENTS_TOOLS)

# Tools by database
TOOLS_BY_DATABASE = {
    "918affd4-ce0d-4b8e-b760-4d972fd24826": EVENTSPROJECTS_TOOLS,
    "ed8ba37a-719a-47d7-a796-c2d373c794b9": MEETINGSANDTASKS_TOOLS,
    "139594e5-2bd9-47af-93ca-bb72a35742d2": TEAMS_TOOLS,
    "55909df8-1f56-40c4-9327-bab99b4f97f5": DOCUMENTS_TOOLS,
}

def get_all_tools() -> List[Tool]:
    """Get all generated tools."""
    return ALL_TOOLS

def get_tools_for_database(database_id: str) -> List[Tool]:
    """Get tools for a specific database."""
    return TOOLS_BY_DATABASE.get(database_id, [])

def get_database_ids() -> List[str]:
    """Get all database IDs."""
    return list(TOOLS_BY_DATABASE.keys())
