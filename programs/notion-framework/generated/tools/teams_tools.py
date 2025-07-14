"""Generated tools for Teams database."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from llmgine.llm.tools import Tool, Parameter
from notion_framework.client.client import NotionClient
from notion_framework.types.filters import FilterBuilder
from notion_framework.types.sorts import SortBuilder

from ..databases.teams import Teams


# CRUD Tools

async def create_teams(
    client: NotionClient,
    name: str,
    __events_projects: Optional[List[str]] = None,
    cover: Optional[List[str]] = None,
    person: Optional[List[str]] = None,
    committee: Optional[List[str]] = None,
    document: Optional[List[str]] = None,
) -> str:
    """Create a new Teams."""
    
    instance = Teams()
    instance.set_client(client)
    
    # Set required properties
    instance.set_name(name)
    
    # Set optional properties
    if __events_projects is not None:
        instance.set___events_projects(__events_projects)
    if cover is not None:
        instance.set_cover(cover)
    if person is not None:
        instance.set_person(person)
    if committee is not None:
        instance.set_committee(committee)
    if document is not None:
        instance.set_document(document)
    
    page_id = await instance.create()
    return f"Created Teams with ID: {page_id}"


async def update_teams(
    client: NotionClient,
    page_id: str,
    __events_projects: Optional[List[str]] = None,
    cover: Optional[List[str]] = None,
    person: Optional[List[str]] = None,
    committee: Optional[List[str]] = None,
    document: Optional[List[str]] = None,
    name: Optional[str] = None,
) -> str:
    """Update an existing Teams."""
    
    # Get current page data
    instance = await Teams.get(client, page_id)
    
    # Update properties that were provided
    if __events_projects is not None:
        instance.set___events_projects(__events_projects)
    if cover is not None:
        instance.set_cover(cover)
    if person is not None:
        instance.set_person(person)
    if committee is not None:
        instance.set_committee(committee)
    if document is not None:
        instance.set_document(document)
    if name is not None:
        instance.set_name(name)
    
    await instance.update(page_id)
    return f"Updated Teams {page_id}"


async def get_teams(
    client: NotionClient,
    page_id: str
) -> str:
    """Get a Teams by ID."""
    
    instance = await Teams.get(client, page_id)
    
    # Format output
    details = []
    if instance.__events_projects is not None:
        details.append(f"💥 Events/Projects: {instance.__events_projects}")
    if instance.cover is not None:
        details.append(f"Cover: {instance.cover}")
    if instance.person is not None:
        details.append(f"Person: {instance.person}")
    if instance.committee is not None:
        details.append(f"Committee: {instance.committee}")
    if instance.document is not None:
        details.append(f"Document: {instance.document}")
    if instance.name is not None:
        details.append(f"Name: {instance.name}")
    
    return f"Teams {page_id}:\n" + "\n".join(details)


async def list_teamss(
    client: NotionClient,
    limit: Optional[int] = 10,
    filter_by_name_contains: Optional[str] = None,
) -> str:
    """List Teamss with optional filtering."""
    
    # Build filters
    filters = []
    if filter_by_name_contains is not None:
        filters.append(Teams.filter_by_name_contains(filter_by_name_contains))
    
    # Combine filters
    filter_condition = None
    if filters:
        if len(filters) == 1:
            filter_condition = filters[0]
        else:
            filter_condition = FilterBuilder().and_(*filters)
    
    # Sort by last edited time (newest first)
    sorts = [SortBuilder().last_edited_time().desc()]
    
    instances = await Teams.list(
        client=client,
        filter_condition=filter_condition,
        sorts=sorts,
        limit=limit
    )
    
    if not instances:
        return "No Teamss found"
    
    # Format results
    results = []
    for instance in instances:
        title = instance.name or "Untitled"
        break
        results.append(f"• {title}")
    
    return f"Found {len(instances)} Teamss:\n" + "\n".join(results)


# Property-specific tools

async def add_teams___events_projects(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to 💥 Events/Projects for a Teams."""
    
    instance = await Teams.get(client, page_id)
    current_relations = instance.get___events_projects() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set___events_projects(current_relations)
        await instance.update(page_id)
        return f"Added relation to 💥 Events/Projects for Teams {page_id}"
    else:
        return f"Relation already exists in 💥 Events/Projects for Teams {page_id}"


async def remove_teams___events_projects(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from 💥 Events/Projects for a Teams."""
    
    instance = await Teams.get(client, page_id)
    current_relations = instance.get___events_projects() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set___events_projects(current_relations)
        await instance.update(page_id)
        return f"Removed relation from 💥 Events/Projects for Teams {page_id}"
    else:
        return f"Relation not found in 💥 Events/Projects for Teams {page_id}"


async def add_teams_committee(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Committee for a Teams."""
    
    instance = await Teams.get(client, page_id)
    current_relations = instance.get_committee() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_committee(current_relations)
        await instance.update(page_id)
        return f"Added relation to Committee for Teams {page_id}"
    else:
        return f"Relation already exists in Committee for Teams {page_id}"


async def remove_teams_committee(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Committee for a Teams."""
    
    instance = await Teams.get(client, page_id)
    current_relations = instance.get_committee() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_committee(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Committee for Teams {page_id}"
    else:
        return f"Relation not found in Committee for Teams {page_id}"


async def add_teams_document(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Document for a Teams."""
    
    instance = await Teams.get(client, page_id)
    current_relations = instance.get_document() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_document(current_relations)
        await instance.update(page_id)
        return f"Added relation to Document for Teams {page_id}"
    else:
        return f"Relation already exists in Document for Teams {page_id}"


async def remove_teams_document(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Document for a Teams."""
    
    instance = await Teams.get(client, page_id)
    current_relations = instance.get_document() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_document(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Document for Teams {page_id}"
    else:
        return f"Relation not found in Document for Teams {page_id}"



# LLMgine Tool Definitions

TOOLS = [
    Tool(
        name="create_teams",
        description="Create a new Teams",
        parameters=[
            Parameter(
                name="name",
                description="Name",
                type="string",
                required=True
            ),
            Parameter(
                name="__events_projects",
                description="💥 Events/Projects",
                type="array",
                required=False
            ),
            Parameter(
                name="cover",
                description="Cover",
                type="array",
                required=False
            ),
            Parameter(
                name="person",
                description="Person",
                type="array",
                required=False
            ),
            Parameter(
                name="committee",
                description="Committee",
                type="array",
                required=False
            ),
            Parameter(
                name="document",
                description="Document",
                type="array",
                required=False
            ),
        ],
        function=create_teams,
        is_async=True
    ),
    Tool(
        name="update_teams",
        description="Update an existing Teams",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="__events_projects",
                description="💥 Events/Projects",
                type="array",
                required=False
            ),
            Parameter(
                name="cover",
                description="Cover",
                type="array",
                required=False
            ),
            Parameter(
                name="person",
                description="Person",
                type="array",
                required=False
            ),
            Parameter(
                name="committee",
                description="Committee",
                type="array",
                required=False
            ),
            Parameter(
                name="document",
                description="Document",
                type="array",
                required=False
            ),
            Parameter(
                name="name",
                description="Name",
                type="string",
                required=False
            ),
        ],
        function=update_teams,
        is_async=True
    ),
    Tool(
        name="get_teams",
        description="Get a Teams by ID",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to retrieve",
                type="str",
                required=True
            )
        ],
        function=get_teams,
        is_async=True
    ),
    Tool(
        name="list_teamss",
        description="List Teamss with optional filtering",
        parameters=[
            Parameter(
                name="limit",
                description="Maximum number of results to return",
                type="int",
                required=False
            ),
            Parameter(
                name="filter_by_name_contains",
                description="Filter by Name containing text",
                type="str",
                required=False
            ),
        ],
        function=list_teamss,
        is_async=True
    ),
    Tool(
        name="add_teams___events_projects",
        description="Add a relation to 💥 Events/Projects for a Teams",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="related_page_id",
                description="ID of the page to relate",
                type="str",
                required=True
            )
        ],
        function=add_teams___events_projects,
        is_async=True
    ),
    Tool(
        name="remove_teams___events_projects",
        description="Remove a relation from 💥 Events/Projects for a Teams",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="related_page_id",
                description="ID of the page to unrelate",
                type="str",
                required=True
            )
        ],
        function=remove_teams___events_projects,
        is_async=True
    ),
    Tool(
        name="add_teams_committee",
        description="Add a relation to Committee for a Teams",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="related_page_id",
                description="ID of the page to relate",
                type="str",
                required=True
            )
        ],
        function=add_teams_committee,
        is_async=True
    ),
    Tool(
        name="remove_teams_committee",
        description="Remove a relation from Committee for a Teams",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="related_page_id",
                description="ID of the page to unrelate",
                type="str",
                required=True
            )
        ],
        function=remove_teams_committee,
        is_async=True
    ),
    Tool(
        name="add_teams_document",
        description="Add a relation to Document for a Teams",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="related_page_id",
                description="ID of the page to relate",
                type="str",
                required=True
            )
        ],
        function=add_teams_document,
        is_async=True
    ),
    Tool(
        name="remove_teams_document",
        description="Remove a relation from Document for a Teams",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="related_page_id",
                description="ID of the page to unrelate",
                type="str",
                required=True
            )
        ],
        function=remove_teams_document,
        is_async=True
    ),
]