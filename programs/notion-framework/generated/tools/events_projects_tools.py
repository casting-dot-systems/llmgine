"""Generated tools for Events/Projects database."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from llmgine.llm.tools import Tool, Parameter
from notion_framework.client.client import NotionClient
from notion_framework.types.filters import FilterBuilder
from notion_framework.types.sorts import SortBuilder

from ..databases.events_projects import EventsProjects


# CRUD Tools

async def create_events_projects(
    client: NotionClient,
    name: str,
    parent_item: Optional[List[str]] = None,
    type: Optional[Optional[Literal["Note", "Event", "Project", "Admin", "Program", "Portfolio", "User Story", "Epic", "Sprint", "Feature"]]] = None,
    owner: Optional[List[str]] = None,
    sub_item: Optional[List[str]] = None,
    allocated: Optional[List[str]] = None,
    team: Optional[List[str]] = None,
    text: Optional[str] = None,
    progress: Optional[Optional[str]] = None,
    priority: Optional[Optional[Literal["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]]] = None,
    description: Optional[str] = None,
    due_date_s_: Optional[Optional[datetime]] = None,
    documents: Optional[List[str]] = None,
    tasks: Optional[List[str]] = None,
    location: Optional[str] = None,
) -> str:
    """Create a new Events/Projects."""
    
    instance = EventsProjects()
    instance.set_client(client)
    
    # Set required properties
    instance.set_name(name)
    
    # Set optional properties
    if parent_item is not None:
        instance.set_parent_item(parent_item)
    if type is not None:
        instance.set_type(type)
    if owner is not None:
        instance.set_owner(owner)
    if sub_item is not None:
        instance.set_sub_item(sub_item)
    if allocated is not None:
        instance.set_allocated(allocated)
    if team is not None:
        instance.set_team(team)
    if text is not None:
        instance.set_text(text)
    if progress is not None:
        instance.set_progress(progress)
    if priority is not None:
        instance.set_priority(priority)
    if description is not None:
        instance.set_description(description)
    if due_date_s_ is not None:
        instance.set_due_date_s_(due_date_s_)
    if documents is not None:
        instance.set_documents(documents)
    if tasks is not None:
        instance.set_tasks(tasks)
    if location is not None:
        instance.set_location(location)
    
    page_id = await instance.create()
    return f"Created Events/Projects with ID: {page_id}"


async def update_events_projects(
    client: NotionClient,
    page_id: str,
    parent_item: Optional[List[str]] = None,
    type: Optional[Optional[Literal["Note", "Event", "Project", "Admin", "Program", "Portfolio", "User Story", "Epic", "Sprint", "Feature"]]] = None,
    owner: Optional[List[str]] = None,
    sub_item: Optional[List[str]] = None,
    allocated: Optional[List[str]] = None,
    team: Optional[List[str]] = None,
    text: Optional[str] = None,
    progress: Optional[Optional[str]] = None,
    priority: Optional[Optional[Literal["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]]] = None,
    description: Optional[str] = None,
    due_date_s_: Optional[Optional[datetime]] = None,
    documents: Optional[List[str]] = None,
    tasks: Optional[List[str]] = None,
    location: Optional[str] = None,
    name: Optional[str] = None,
) -> str:
    """Update an existing Events/Projects."""
    
    # Get current page data
    instance = await EventsProjects.get(client, page_id)
    
    # Update properties that were provided
    if parent_item is not None:
        instance.set_parent_item(parent_item)
    if type is not None:
        instance.set_type(type)
    if owner is not None:
        instance.set_owner(owner)
    if sub_item is not None:
        instance.set_sub_item(sub_item)
    if allocated is not None:
        instance.set_allocated(allocated)
    if team is not None:
        instance.set_team(team)
    if text is not None:
        instance.set_text(text)
    if progress is not None:
        instance.set_progress(progress)
    if priority is not None:
        instance.set_priority(priority)
    if description is not None:
        instance.set_description(description)
    if due_date_s_ is not None:
        instance.set_due_date_s_(due_date_s_)
    if documents is not None:
        instance.set_documents(documents)
    if tasks is not None:
        instance.set_tasks(tasks)
    if location is not None:
        instance.set_location(location)
    if name is not None:
        instance.set_name(name)
    
    await instance.update(page_id)
    return f"Updated Events/Projects {page_id}"


async def get_events_projects(
    client: NotionClient,
    page_id: str
) -> str:
    """Get a Events/Projects by ID."""
    
    instance = await EventsProjects.get(client, page_id)
    
    # Format output
    details = []
    if instance.parent_item is not None:
        details.append(f"Parent item: {instance.parent_item}")
    if instance.type is not None:
        details.append(f"Type: {instance.type}")
    if instance.owner is not None:
        details.append(f"Owner: {instance.owner}")
    if instance.sub_item is not None:
        details.append(f"Sub-item: {instance.sub_item}")
    if instance.allocated is not None:
        details.append(f"Allocated: {instance.allocated}")
    if instance.team is not None:
        details.append(f"Team: {instance.team}")
    if instance.text is not None:
        details.append(f"Text: {instance.text}")
    if instance.progress is not None:
        details.append(f"Progress: {instance.progress}")
    if instance.priority is not None:
        details.append(f"Priority: {instance.priority}")
    if instance.description is not None:
        details.append(f"Description: {instance.description}")
    if instance.due_date_s_ is not None:
        details.append(f"Due Date(s): {instance.due_date_s_}")
    if instance.documents is not None:
        details.append(f"Documents: {instance.documents}")
    if instance.tasks is not None:
        details.append(f"Tasks: {instance.tasks}")
    if instance.location is not None:
        details.append(f"Location: {instance.location}")
    if instance.name is not None:
        details.append(f"Name: {instance.name}")
    
    return f"Events/Projects {page_id}:\n" + "\n".join(details)


async def list_events_projectss(
    client: NotionClient,
    limit: Optional[int] = 10,
    filter_by_type: Optional[str] = None,
    filter_by_text_contains: Optional[str] = None,
    filter_by_progress: Optional[str] = None,
    filter_by_priority: Optional[str] = None,
    filter_by_description_contains: Optional[str] = None,
    filter_by_location_contains: Optional[str] = None,
    filter_by_name_contains: Optional[str] = None,
) -> str:
    """List Events/Projectss with optional filtering."""
    
    # Build filters
    filters = []
    if filter_by_type is not None:
        filters.append(EventsProjects.filter_by_type(filter_by_type))
    if filter_by_text_contains is not None:
        filters.append(EventsProjects.filter_by_text_contains(filter_by_text_contains))
    if filter_by_progress is not None:
        filters.append(EventsProjects.filter_by_progress(filter_by_progress))
    if filter_by_priority is not None:
        filters.append(EventsProjects.filter_by_priority(filter_by_priority))
    if filter_by_description_contains is not None:
        filters.append(EventsProjects.filter_by_description_contains(filter_by_description_contains))
    if filter_by_location_contains is not None:
        filters.append(EventsProjects.filter_by_location_contains(filter_by_location_contains))
    if filter_by_name_contains is not None:
        filters.append(EventsProjects.filter_by_name_contains(filter_by_name_contains))
    
    # Combine filters
    filter_condition = None
    if filters:
        if len(filters) == 1:
            filter_condition = filters[0]
        else:
            filter_condition = FilterBuilder().and_(*filters)
    
    # Sort by last edited time (newest first)
    sorts = [SortBuilder().last_edited_time().desc()]
    
    instances = await EventsProjects.list(
        client=client,
        filter_condition=filter_condition,
        sorts=sorts,
        limit=limit
    )
    
    if not instances:
        return "No Events/Projectss found"
    
    # Format results
    results = []
    for instance in instances:
        title = instance.name or "Untitled"
        break
        results.append(f"• {title}")
    
    return f"Found {len(instances)} Events/Projectss:\n" + "\n".join(results)


# Property-specific tools

async def add_events_projects_parent_item(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Parent item for a Events/Projects."""
    
    instance = await EventsProjects.get(client, page_id)
    current_relations = instance.get_parent_item() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_parent_item(current_relations)
        await instance.update(page_id)
        return f"Added relation to Parent item for Events/Projects {page_id}"
    else:
        return f"Relation already exists in Parent item for Events/Projects {page_id}"


async def remove_events_projects_parent_item(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Parent item for a Events/Projects."""
    
    instance = await EventsProjects.get(client, page_id)
    current_relations = instance.get_parent_item() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_parent_item(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Parent item for Events/Projects {page_id}"
    else:
        return f"Relation not found in Parent item for Events/Projects {page_id}"


async def set_events_projects_type(
    client: NotionClient,
    page_id: str,
    type: str
) -> str:
    """Set Type for a Events/Projects."""
    
    # Validate the value
    valid_options = ["Note", "Event", "Project", "Admin", "Program", "Portfolio", "User Story", "Epic", "Sprint", "Feature"]
    if type not in valid_options:
        return f"Invalid Type. Valid options: {', '.join(valid_options)}"
    
    instance = await EventsProjects.get(client, page_id)
    instance.set_type(type)
    await instance.update(page_id)
    
    return f"Set Type to '{type}' for Events/Projects {page_id}"


async def add_events_projects_sub_item(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Sub-item for a Events/Projects."""
    
    instance = await EventsProjects.get(client, page_id)
    current_relations = instance.get_sub_item() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_sub_item(current_relations)
        await instance.update(page_id)
        return f"Added relation to Sub-item for Events/Projects {page_id}"
    else:
        return f"Relation already exists in Sub-item for Events/Projects {page_id}"


async def remove_events_projects_sub_item(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Sub-item for a Events/Projects."""
    
    instance = await EventsProjects.get(client, page_id)
    current_relations = instance.get_sub_item() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_sub_item(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Sub-item for Events/Projects {page_id}"
    else:
        return f"Relation not found in Sub-item for Events/Projects {page_id}"


async def add_events_projects_team(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Team for a Events/Projects."""
    
    instance = await EventsProjects.get(client, page_id)
    current_relations = instance.get_team() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_team(current_relations)
        await instance.update(page_id)
        return f"Added relation to Team for Events/Projects {page_id}"
    else:
        return f"Relation already exists in Team for Events/Projects {page_id}"


async def remove_events_projects_team(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Team for a Events/Projects."""
    
    instance = await EventsProjects.get(client, page_id)
    current_relations = instance.get_team() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_team(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Team for Events/Projects {page_id}"
    else:
        return f"Relation not found in Team for Events/Projects {page_id}"


async def set_events_projects_progress(
    client: NotionClient,
    page_id: str,
    progress: str
) -> str:
    """Set Progress for a Events/Projects."""
    
    # Validate the value
    valid_options = ["On-Going", "Proposal", "Approved", "Planning", "In-Progress", "Finished", "Cancelled", "Archive", "Paused", "To-Review", "Complete"]
    if progress not in valid_options:
        return f"Invalid Progress. Valid options: {', '.join(valid_options)}"
    
    instance = await EventsProjects.get(client, page_id)
    instance.set_progress(progress)
    await instance.update(page_id)
    
    return f"Set Progress to '{progress}' for Events/Projects {page_id}"


async def set_events_projects_priority(
    client: NotionClient,
    page_id: str,
    priority: str
) -> str:
    """Set Priority for a Events/Projects."""
    
    # Validate the value
    valid_options = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
    if priority not in valid_options:
        return f"Invalid Priority. Valid options: {', '.join(valid_options)}"
    
    instance = await EventsProjects.get(client, page_id)
    instance.set_priority(priority)
    await instance.update(page_id)
    
    return f"Set Priority to '{priority}' for Events/Projects {page_id}"


async def add_events_projects_documents(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Documents for a Events/Projects."""
    
    instance = await EventsProjects.get(client, page_id)
    current_relations = instance.get_documents() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_documents(current_relations)
        await instance.update(page_id)
        return f"Added relation to Documents for Events/Projects {page_id}"
    else:
        return f"Relation already exists in Documents for Events/Projects {page_id}"


async def remove_events_projects_documents(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Documents for a Events/Projects."""
    
    instance = await EventsProjects.get(client, page_id)
    current_relations = instance.get_documents() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_documents(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Documents for Events/Projects {page_id}"
    else:
        return f"Relation not found in Documents for Events/Projects {page_id}"


async def add_events_projects_tasks(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Tasks for a Events/Projects."""
    
    instance = await EventsProjects.get(client, page_id)
    current_relations = instance.get_tasks() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_tasks(current_relations)
        await instance.update(page_id)
        return f"Added relation to Tasks for Events/Projects {page_id}"
    else:
        return f"Relation already exists in Tasks for Events/Projects {page_id}"


async def remove_events_projects_tasks(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Tasks for a Events/Projects."""
    
    instance = await EventsProjects.get(client, page_id)
    current_relations = instance.get_tasks() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_tasks(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Tasks for Events/Projects {page_id}"
    else:
        return f"Relation not found in Tasks for Events/Projects {page_id}"



# LLMgine Tool Definitions

TOOLS = [
    Tool(
        name="create_events_projects",
        description="Create a new Events/Projects",
        parameters=[
            Parameter(
                name="name",
                description="Name",
                type="string",
                required=True
            ),
            Parameter(
                name="parent_item",
                description="Parent item",
                type="array",
                required=False
            ),
            Parameter(
                name="type",
                description="Type",
                type="string",
                required=False
            ),
            Parameter(
                name="owner",
                description="Owner",
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
                name="allocated",
                description="Allocated",
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
                name="text",
                description="Text",
                type="string",
                required=False
            ),
            Parameter(
                name="progress",
                description="Progress",
                type="string",
                required=False
            ),
            Parameter(
                name="priority",
                description="Priority",
                type="string",
                required=False
            ),
            Parameter(
                name="description",
                description="Description",
                type="string",
                required=False
            ),
            Parameter(
                name="due_date_s_",
                description="Due Date(s)",
                type="string",
                required=False
            ),
            Parameter(
                name="documents",
                description="Documents",
                type="array",
                required=False
            ),
            Parameter(
                name="tasks",
                description="Tasks",
                type="array",
                required=False
            ),
            Parameter(
                name="location",
                description="Location",
                type="string",
                required=False
            ),
        ],
        function=create_events_projects,
        is_async=True
    ),
    Tool(
        name="update_events_projects",
        description="Update an existing Events/Projects",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="parent_item",
                description="Parent item",
                type="array",
                required=False
            ),
            Parameter(
                name="type",
                description="Type",
                type="string",
                required=False
            ),
            Parameter(
                name="owner",
                description="Owner",
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
                name="allocated",
                description="Allocated",
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
                name="text",
                description="Text",
                type="string",
                required=False
            ),
            Parameter(
                name="progress",
                description="Progress",
                type="string",
                required=False
            ),
            Parameter(
                name="priority",
                description="Priority",
                type="string",
                required=False
            ),
            Parameter(
                name="description",
                description="Description",
                type="string",
                required=False
            ),
            Parameter(
                name="due_date_s_",
                description="Due Date(s)",
                type="string",
                required=False
            ),
            Parameter(
                name="documents",
                description="Documents",
                type="array",
                required=False
            ),
            Parameter(
                name="tasks",
                description="Tasks",
                type="array",
                required=False
            ),
            Parameter(
                name="location",
                description="Location",
                type="string",
                required=False
            ),
            Parameter(
                name="name",
                description="Name",
                type="string",
                required=False
            ),
        ],
        function=update_events_projects,
        is_async=True
    ),
    Tool(
        name="get_events_projects",
        description="Get a Events/Projects by ID",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to retrieve",
                type="str",
                required=True
            )
        ],
        function=get_events_projects,
        is_async=True
    ),
    Tool(
        name="list_events_projectss",
        description="List Events/Projectss with optional filtering",
        parameters=[
            Parameter(
                name="limit",
                description="Maximum number of results to return",
                type="int",
                required=False
            ),
            Parameter(
                name="filter_by_type",
                description="Filter by Type",
                type="str",
                required=False
            ),
            Parameter(
                name="filter_by_text_contains",
                description="Filter by Text containing text",
                type="str",
                required=False
            ),
            Parameter(
                name="filter_by_progress",
                description="Filter by Progress",
                type="str",
                required=False
            ),
            Parameter(
                name="filter_by_priority",
                description="Filter by Priority",
                type="str",
                required=False
            ),
            Parameter(
                name="filter_by_description_contains",
                description="Filter by Description containing text",
                type="str",
                required=False
            ),
            Parameter(
                name="filter_by_location_contains",
                description="Filter by Location containing text",
                type="str",
                required=False
            ),
            Parameter(
                name="filter_by_name_contains",
                description="Filter by Name containing text",
                type="str",
                required=False
            ),
        ],
        function=list_events_projectss,
        is_async=True
    ),
    Tool(
        name="add_events_projects_parent_item",
        description="Add a relation to Parent item for a Events/Projects",
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
        function=add_events_projects_parent_item,
        is_async=True
    ),
    Tool(
        name="remove_events_projects_parent_item",
        description="Remove a relation from Parent item for a Events/Projects",
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
        function=remove_events_projects_parent_item,
        is_async=True
    ),
    Tool(
        name="set_events_projects_type",
        description="Set Type for a Events/Projects",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="type",
                description="Type value",
                type="str",
                required=True
            )
        ],
        function=set_events_projects_type,
        is_async=True
    ),
    Tool(
        name="add_events_projects_sub_item",
        description="Add a relation to Sub-item for a Events/Projects",
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
        function=add_events_projects_sub_item,
        is_async=True
    ),
    Tool(
        name="remove_events_projects_sub_item",
        description="Remove a relation from Sub-item for a Events/Projects",
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
        function=remove_events_projects_sub_item,
        is_async=True
    ),
    Tool(
        name="add_events_projects_team",
        description="Add a relation to Team for a Events/Projects",
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
        function=add_events_projects_team,
        is_async=True
    ),
    Tool(
        name="remove_events_projects_team",
        description="Remove a relation from Team for a Events/Projects",
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
        function=remove_events_projects_team,
        is_async=True
    ),
    Tool(
        name="set_events_projects_progress",
        description="Set Progress for a Events/Projects",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="progress",
                description="Progress value",
                type="str",
                required=True
            )
        ],
        function=set_events_projects_progress,
        is_async=True
    ),
    Tool(
        name="set_events_projects_priority",
        description="Set Priority for a Events/Projects",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="priority",
                description="Priority value",
                type="str",
                required=True
            )
        ],
        function=set_events_projects_priority,
        is_async=True
    ),
    Tool(
        name="add_events_projects_documents",
        description="Add a relation to Documents for a Events/Projects",
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
        function=add_events_projects_documents,
        is_async=True
    ),
    Tool(
        name="remove_events_projects_documents",
        description="Remove a relation from Documents for a Events/Projects",
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
        function=remove_events_projects_documents,
        is_async=True
    ),
    Tool(
        name="add_events_projects_tasks",
        description="Add a relation to Tasks for a Events/Projects",
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
        function=add_events_projects_tasks,
        is_async=True
    ),
    Tool(
        name="remove_events_projects_tasks",
        description="Remove a relation from Tasks for a Events/Projects",
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
        function=remove_events_projects_tasks,
        is_async=True
    ),
]