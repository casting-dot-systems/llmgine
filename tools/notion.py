import os
from typing import Dict, List, Optional
from notion_client import Client
import src.framework.clients
from src.framework.tool_calling import openai_function_wrapper
import dotenv
import pprint
import src

dotenv.load_dotenv()

notion = Client(auth=os.environ["NOTION_TOKEN"])

# Database IDs
PROJECTS_TABLE_ID = "918affd4ce0d4b8eb7604d972fd24826"
TASKS_TABLE_ID = "ed8ba37a719a47d7a796c2d373c794b9"
DOCUMENTS_TABLE_ID = "55909df81f5640c49327bab99b4f97f5"
PEOPLE_TABLE_ID = "f56fb0218a4b41718ac610e6f1aa06cb"


# Common Functions
def _format_rich_text(text: str) -> List[Dict]:
    """Helper to format text for Notion API"""
    return [{"type": "text", "text": {"content": text}}]


def _format_title(text: str) -> List[Dict]:
    """Helper to format title for Notion API"""
    return [{"type": "title", "text": {"content": text}}]


# Original Project-specific Functions
@openai_function_wrapper(
    funct_descript="Query projects database to get projects that are on-going",
    param_descript={},
)
def query_projects_database():
    return notion.databases.query(
        database_id=PROJECTS_TABLE_ID,
        filter={
            "and": [
                {"property": "Type", "select": {"equals": "Project"}},
                {"property": "Progress", "select": {"equals": "On-Going"}},
            ]
        },
    )


@openai_function_wrapper(
    funct_descript="Query tasks database to get tasks for a project",
    param_descript={"project_id": "The project ID to get tasks for"},
)
def get_project_tasks(project_id: str):
    return notion.databases.query(
        database_id=TASKS_TABLE_ID,
        filter={"property": "Event/Project", "relation": {"contains": project_id}},
    )


@openai_function_wrapper(
    funct_descript="Query documents database to get documents for a project",
    param_descript={"project_id": "The project ID to get documents for"},
)
def get_project_documents(project_id: str):
    return notion.databases.query(
        database_id=DOCUMENTS_TABLE_ID,
        filter={"property": "Events/Projects", "relation": {"contains": project_id}},
    )


@openai_function_wrapper(
    funct_descript="Read inside a document",
    param_descript={"document_id": "The document ID to read"},
)
def read_document(document_id: str):
    return notion.blocks.children.list(block_id=document_id)
