"""Generated tools for Documents database."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from llmgine.llm.tools import Tool, Parameter
from notion_framework.client.client import NotionClient
from notion_framework.types.filters import FilterBuilder
from notion_framework.types.sorts import SortBuilder

from ..databases.documents import Documents


# CRUD Tools

async def create_documents(
    client: NotionClient,
    name: str,
    events_projects: Optional[List[str]] = None,
    parent_item: Optional[List[str]] = None,
    google_drive_file: Optional[List[str]] = None,
    person: Optional[List[str]] = None,
    contributors: Optional[List[str]] = None,
    team: Optional[List[str]] = None,
    pinned: Optional[bool] = None,
    owned_by: Optional[List[str]] = None,
    sub_item: Optional[List[str]] = None,
    in_charge: Optional[List[str]] = None,
    status: Optional[Optional[str]] = None,
) -> str:
    """Create a new Documents."""
    
    instance = Documents()
    instance.set_client(client)
    
    # Set required properties
    instance.set_name(name)
    
    # Set optional properties
    if events_projects is not None:
        instance.set_events_projects(events_projects)
    if parent_item is not None:
        instance.set_parent_item(parent_item)
    if google_drive_file is not None:
        instance.set_google_drive_file(google_drive_file)
    if person is not None:
        instance.set_person(person)
    if contributors is not None:
        instance.set_contributors(contributors)
    if team is not None:
        instance.set_team(team)
    if pinned is not None:
        instance.set_pinned(pinned)
    if owned_by is not None:
        instance.set_owned_by(owned_by)
    if sub_item is not None:
        instance.set_sub_item(sub_item)
    if in_charge is not None:
        instance.set_in_charge(in_charge)
    if status is not None:
        instance.set_status(status)
    
    page_id = await instance.create()
    return f"Created Documents with ID: {page_id}"


async def update_documents(
    client: NotionClient,
    page_id: str,
    events_projects: Optional[List[str]] = None,
    parent_item: Optional[List[str]] = None,
    google_drive_file: Optional[List[str]] = None,
    person: Optional[List[str]] = None,
    contributors: Optional[List[str]] = None,
    team: Optional[List[str]] = None,
    pinned: Optional[bool] = None,
    owned_by: Optional[List[str]] = None,
    sub_item: Optional[List[str]] = None,
    name: Optional[str] = None,
    in_charge: Optional[List[str]] = None,
    status: Optional[Optional[str]] = None,
) -> str:
    """Update an existing Documents."""
    
    # Get current page data
    instance = await Documents.get(client, page_id)
    
    # Update properties that were provided
    if events_projects is not None:
        instance.set_events_projects(events_projects)
    if parent_item is not None:
        instance.set_parent_item(parent_item)
    if google_drive_file is not None:
        instance.set_google_drive_file(google_drive_file)
    if person is not None:
        instance.set_person(person)
    if contributors is not None:
        instance.set_contributors(contributors)
    if team is not None:
        instance.set_team(team)
    if pinned is not None:
        instance.set_pinned(pinned)
    if owned_by is not None:
        instance.set_owned_by(owned_by)
    if sub_item is not None:
        instance.set_sub_item(sub_item)
    if name is not None:
        instance.set_name(name)
    if in_charge is not None:
        instance.set_in_charge(in_charge)
    if status is not None:
        instance.set_status(status)
    
    await instance.update(page_id)
    return f"Updated Documents {page_id}"


async def get_documents(
    client: NotionClient,
    page_id: str
) -> str:
    """Get a Documents by ID."""
    
    instance = await Documents.get(client, page_id)
    
    # Format output
    details = []
    if instance.events_projects is not None:
        details.append(f"Events/Projects: {instance.events_projects}")
    if instance.parent_item is not None:
        details.append(f"Parent item: {instance.parent_item}")
    if instance.last_edited_by is not None:
        details.append(f"Last edited by: {instance.last_edited_by}")
    if instance.google_drive_file is not None:
        details.append(f"Google Drive File: {instance.google_drive_file}")
    if instance.person is not None:
        details.append(f"Person: {instance.person}")
    if instance.contributors is not None:
        details.append(f"Contributors: {instance.contributors}")
    if instance.team is not None:
        details.append(f"Team: {instance.team}")
    if instance.pinned is not None:
        details.append(f"Pinned: {instance.pinned}")
    if instance.owned_by is not None:
        details.append(f"Owned By: {instance.owned_by}")
    if instance.sub_item is not None:
        details.append(f"Sub-item: {instance.sub_item}")
    if instance.name is not None:
        details.append(f"Name: {instance.name}")
    if instance.in_charge is not None:
        details.append(f"In Charge: {instance.in_charge}")
    if instance.status is not None:
        details.append(f"Status: {instance.status}")
    
    return f"Documents {page_id}:\n" + "\n".join(details)


async def list_documentss(
    client: NotionClient,
    limit: Optional[int] = 10,
    filter_by_pinned: Optional[bool] = None,
    filter_by_name_contains: Optional[str] = None,
) -> str:
    """List Documentss with optional filtering."""
    
    # Build filters
    filters = []
    if filter_by_pinned is not None:
        filters.append(Documents.filter_by_pinned(filter_by_pinned))
    if filter_by_name_contains is not None:
        filters.append(Documents.filter_by_name_contains(filter_by_name_contains))
    
    # Combine filters
    filter_condition = None
    if filters:
        if len(filters) == 1:
            filter_condition = filters[0]
        else:
            filter_condition = FilterBuilder().and_(*filters)
    
    # Sort by last edited time (newest first)
    sorts = [SortBuilder().last_edited_time().desc()]
    
    instances = await Documents.list(
        client=client,
        filter_condition=filter_condition,
        sorts=sorts,
        limit=limit
    )
    
    if not instances:
        return "No Documentss found"
    
    # Format results
    results = []
    for instance in instances:
        title = instance.name or "Untitled"
        break
        results.append(f"• {title}")
    
    return f"Found {len(instances)} Documentss:\n" + "\n".join(results)


# Property-specific tools

async def add_documents_events_projects(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Events/Projects for a Documents."""
    
    instance = await Documents.get(client, page_id)
    current_relations = instance.get_events_projects() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_events_projects(current_relations)
        await instance.update(page_id)
        return f"Added relation to Events/Projects for Documents {page_id}"
    else:
        return f"Relation already exists in Events/Projects for Documents {page_id}"


async def remove_documents_events_projects(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Events/Projects for a Documents."""
    
    instance = await Documents.get(client, page_id)
    current_relations = instance.get_events_projects() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_events_projects(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Events/Projects for Documents {page_id}"
    else:
        return f"Relation not found in Events/Projects for Documents {page_id}"


async def add_documents_parent_item(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Parent item for a Documents."""
    
    instance = await Documents.get(client, page_id)
    current_relations = instance.get_parent_item() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_parent_item(current_relations)
        await instance.update(page_id)
        return f"Added relation to Parent item for Documents {page_id}"
    else:
        return f"Relation already exists in Parent item for Documents {page_id}"


async def remove_documents_parent_item(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Parent item for a Documents."""
    
    instance = await Documents.get(client, page_id)
    current_relations = instance.get_parent_item() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_parent_item(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Parent item for Documents {page_id}"
    else:
        return f"Relation not found in Parent item for Documents {page_id}"


async def add_documents_google_drive_file(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Google Drive File for a Documents."""
    
    instance = await Documents.get(client, page_id)
    current_relations = instance.get_google_drive_file() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_google_drive_file(current_relations)
        await instance.update(page_id)
        return f"Added relation to Google Drive File for Documents {page_id}"
    else:
        return f"Relation already exists in Google Drive File for Documents {page_id}"


async def remove_documents_google_drive_file(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Google Drive File for a Documents."""
    
    instance = await Documents.get(client, page_id)
    current_relations = instance.get_google_drive_file() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_google_drive_file(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Google Drive File for Documents {page_id}"
    else:
        return f"Relation not found in Google Drive File for Documents {page_id}"


async def add_documents_team(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Team for a Documents."""
    
    instance = await Documents.get(client, page_id)
    current_relations = instance.get_team() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_team(current_relations)
        await instance.update(page_id)
        return f"Added relation to Team for Documents {page_id}"
    else:
        return f"Relation already exists in Team for Documents {page_id}"


async def remove_documents_team(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Team for a Documents."""
    
    instance = await Documents.get(client, page_id)
    current_relations = instance.get_team() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_team(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Team for Documents {page_id}"
    else:
        return f"Relation not found in Team for Documents {page_id}"


async def toggle_documents_pinned(
    client: NotionClient,
    page_id: str
) -> str:
    """Toggle Pinned for a Documents."""
    
    instance = await Documents.get(client, page_id)
    current_value = instance.get_pinned()
    new_value = not current_value
    
    instance.set_pinned(new_value)
    await instance.update(page_id)
    
    return f"Toggled Pinned to {new_value} for Documents {page_id}"


async def add_documents_sub_item(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Sub-item for a Documents."""
    
    instance = await Documents.get(client, page_id)
    current_relations = instance.get_sub_item() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_sub_item(current_relations)
        await instance.update(page_id)
        return f"Added relation to Sub-item for Documents {page_id}"
    else:
        return f"Relation already exists in Sub-item for Documents {page_id}"


async def remove_documents_sub_item(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Sub-item for a Documents."""
    
    instance = await Documents.get(client, page_id)
    current_relations = instance.get_sub_item() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_sub_item(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Sub-item for Documents {page_id}"
    else:
        return f"Relation not found in Sub-item for Documents {page_id}"



# LLMgine Tool Definitions

TOOLS = [
    Tool(
        name="create_documents",
        description="Create a new Documents",
        parameters=[
            Parameter(
                name="name",
                description="Name",
                type="string",
                required=True
            ),
            Parameter(
                name="events_projects",
                description="Events/Projects",
                type="array",
                required=False
            ),
            Parameter(
                name="parent_item",
                description="Parent item",
                type="array",
                required=False
            ),
            Parameter(
                name="google_drive_file",
                description="Google Drive File",
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
                name="contributors",
                description="Contributors",
                type="array",
                required=False
            ),
            Parameter(
                name="team",
                description="Team",
                type="array",
                required=False
            ),
            Parameter(
                name="pinned",
                description="Pinned",
                type="boolean",
                required=False
            ),
            Parameter(
                name="owned_by",
                description="Owned By",
                type="array",
                required=False
            ),
            Parameter(
                name="sub_item",
                description="Sub-item",
                type="array",
                required=False
            ),
            Parameter(
                name="in_charge",
                description="In Charge",
                type="array",
                required=False
            ),
            Parameter(
                name="status",
                description="Status",
                type="string",
                required=False
            ),
        ],
        function=create_documents,
        is_async=True
    ),
    Tool(
        name="update_documents",
        description="Update an existing Documents",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="events_projects",
                description="Events/Projects",
                type="array",
                required=False
            ),
            Parameter(
                name="parent_item",
                description="Parent item",
                type="array",
                required=False
            ),
            Parameter(
                name="google_drive_file",
                description="Google Drive File",
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
                name="contributors",
                description="Contributors",
                type="array",
                required=False
            ),
            Parameter(
                name="team",
                description="Team",
                type="array",
                required=False
            ),
            Parameter(
                name="pinned",
                description="Pinned",
                type="boolean",
                required=False
            ),
            Parameter(
                name="owned_by",
                description="Owned By",
                type="array",
                required=False
            ),
            Parameter(
                name="sub_item",
                description="Sub-item",
                type="array",
                required=False
            ),
            Parameter(
                name="name",
                description="Name",
                type="string",
                required=False
            ),
            Parameter(
                name="in_charge",
                description="In Charge",
                type="array",
                required=False
            ),
            Parameter(
                name="status",
                description="Status",
                type="string",
                required=False
            ),
        ],
        function=update_documents,
        is_async=True
    ),
    Tool(
        name="get_documents",
        description="Get a Documents by ID",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to retrieve",
                type="str",
                required=True
            )
        ],
        function=get_documents,
        is_async=True
    ),
    Tool(
        name="list_documentss",
        description="List Documentss with optional filtering",
        parameters=[
            Parameter(
                name="limit",
                description="Maximum number of results to return",
                type="int",
                required=False
            ),
            Parameter(
                name="filter_by_pinned",
                description="Filter by Pinned",
                type="bool",
                required=False
            ),
            Parameter(
                name="filter_by_name_contains",
                description="Filter by Name containing text",
                type="str",
                required=False
            ),
        ],
        function=list_documentss,
        is_async=True
    ),
    Tool(
        name="add_documents_events_projects",
        description="Add a relation to Events/Projects for a Documents",
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
        function=add_documents_events_projects,
        is_async=True
    ),
    Tool(
        name="remove_documents_events_projects",
        description="Remove a relation from Events/Projects for a Documents",
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
        function=remove_documents_events_projects,
        is_async=True
    ),
    Tool(
        name="add_documents_parent_item",
        description="Add a relation to Parent item for a Documents",
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
        function=add_documents_parent_item,
        is_async=True
    ),
    Tool(
        name="remove_documents_parent_item",
        description="Remove a relation from Parent item for a Documents",
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
        function=remove_documents_parent_item,
        is_async=True
    ),
    Tool(
        name="add_documents_google_drive_file",
        description="Add a relation to Google Drive File for a Documents",
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
        function=add_documents_google_drive_file,
        is_async=True
    ),
    Tool(
        name="remove_documents_google_drive_file",
        description="Remove a relation from Google Drive File for a Documents",
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
        function=remove_documents_google_drive_file,
        is_async=True
    ),
    Tool(
        name="add_documents_team",
        description="Add a relation to Team for a Documents",
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
        function=add_documents_team,
        is_async=True
    ),
    Tool(
        name="remove_documents_team",
        description="Remove a relation from Team for a Documents",
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
        function=remove_documents_team,
        is_async=True
    ),
    Tool(
        name="toggle_documents_pinned",
        description="Toggle Pinned for a Documents",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            )
        ],
        function=toggle_documents_pinned,
        is_async=True
    ),
    Tool(
        name="add_documents_sub_item",
        description="Add a relation to Sub-item for a Documents",
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
        function=add_documents_sub_item,
        is_async=True
    ),
    Tool(
        name="remove_documents_sub_item",
        description="Remove a relation from Sub-item for a Documents",
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
        function=remove_documents_sub_item,
        is_async=True
    ),
]