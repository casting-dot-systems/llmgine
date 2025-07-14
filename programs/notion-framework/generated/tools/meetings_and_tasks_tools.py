"""Generated tools for Meetings and Tasks database."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from llmgine.llm.tools import Tool, Parameter
from notion_framework.client.client import NotionClient
from notion_framework.types.filters import FilterBuilder
from notion_framework.types.sorts import SortBuilder

from ..databases.meetings_and_tasks import MeetingsAndTasks


# CRUD Tools

async def create_meetings_and_tasks(
    client: NotionClient,
    name: str,
    status: Optional[Optional[str]] = None,
    blocking: Optional[List[str]] = None,
    due_dates: Optional[Optional[datetime]] = None,
    parent_task: Optional[List[str]] = None,
    blocked_by: Optional[List[str]] = None,
    sub_task: Optional[List[str]] = None,
    in_charge: Optional[List[str]] = None,
    task_progress: Optional[str] = None,
    event_project: Optional[List[str]] = None,
    team: Optional[List[str]] = None,
    priority: Optional[Optional[Literal["Low", "Medium", "High"]]] = None,
    description: Optional[str] = None,
) -> str:
    """Create a new Meetings and Tasks."""
    
    instance = MeetingsAndTasks()
    instance.set_client(client)
    
    # Set required properties
    instance.set_name(name)
    
    # Set optional properties
    if status is not None:
        instance.set_status(status)
    if blocking is not None:
        instance.set_blocking(blocking)
    if due_dates is not None:
        instance.set_due_dates(due_dates)
    if parent_task is not None:
        instance.set_parent_task(parent_task)
    if blocked_by is not None:
        instance.set_blocked_by(blocked_by)
    if sub_task is not None:
        instance.set_sub_task(sub_task)
    if in_charge is not None:
        instance.set_in_charge(in_charge)
    if task_progress is not None:
        instance.set_task_progress(task_progress)
    if event_project is not None:
        instance.set_event_project(event_project)
    if team is not None:
        instance.set_team(team)
    if priority is not None:
        instance.set_priority(priority)
    if description is not None:
        instance.set_description(description)
    
    page_id = await instance.create()
    return f"Created Meetings and Tasks with ID: {page_id}"


async def update_meetings_and_tasks(
    client: NotionClient,
    page_id: str,
    status: Optional[Optional[str]] = None,
    blocking: Optional[List[str]] = None,
    due_dates: Optional[Optional[datetime]] = None,
    parent_task: Optional[List[str]] = None,
    blocked_by: Optional[List[str]] = None,
    sub_task: Optional[List[str]] = None,
    in_charge: Optional[List[str]] = None,
    task_progress: Optional[str] = None,
    event_project: Optional[List[str]] = None,
    team: Optional[List[str]] = None,
    name: Optional[str] = None,
    priority: Optional[Optional[Literal["Low", "Medium", "High"]]] = None,
    description: Optional[str] = None,
) -> str:
    """Update an existing Meetings and Tasks."""
    
    # Get current page data
    instance = await MeetingsAndTasks.get(client, page_id)
    
    # Update properties that were provided
    if status is not None:
        instance.set_status(status)
    if blocking is not None:
        instance.set_blocking(blocking)
    if due_dates is not None:
        instance.set_due_dates(due_dates)
    if parent_task is not None:
        instance.set_parent_task(parent_task)
    if blocked_by is not None:
        instance.set_blocked_by(blocked_by)
    if sub_task is not None:
        instance.set_sub_task(sub_task)
    if in_charge is not None:
        instance.set_in_charge(in_charge)
    if task_progress is not None:
        instance.set_task_progress(task_progress)
    if event_project is not None:
        instance.set_event_project(event_project)
    if team is not None:
        instance.set_team(team)
    if name is not None:
        instance.set_name(name)
    if priority is not None:
        instance.set_priority(priority)
    if description is not None:
        instance.set_description(description)
    
    await instance.update(page_id)
    return f"Updated Meetings and Tasks {page_id}"


async def get_meetings_and_tasks(
    client: NotionClient,
    page_id: str
) -> str:
    """Get a Meetings and Tasks by ID."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    
    # Format output
    details = []
    if instance.due_date is not None:
        details.append(f"Due Date: {instance.due_date}")
    if instance.status is not None:
        details.append(f"Status: {instance.status}")
    if instance.blocking is not None:
        details.append(f"Blocking: {instance.blocking}")
    if instance.due_dates is not None:
        details.append(f"Due Dates: {instance.due_dates}")
    if instance.parent_task is not None:
        details.append(f"Parent task: {instance.parent_task}")
    if instance.blocked_by is not None:
        details.append(f"Blocked by: {instance.blocked_by}")
    if instance.last_edited_time is not None:
        details.append(f"Last edited time: {instance.last_edited_time}")
    if instance.sub_task is not None:
        details.append(f"Sub-task: {instance.sub_task}")
    if instance.in_charge is not None:
        details.append(f"In Charge: {instance.in_charge}")
    if instance.is_due_ is not None:
        details.append(f"Is Due : {instance.is_due_}")
    if instance.task_progress is not None:
        details.append(f"Task Progress: {instance.task_progress}")
    if instance.last_edited_by is not None:
        details.append(f"Last edited by: {instance.last_edited_by}")
    if instance.event_project is not None:
        details.append(f"Event/Project: {instance.event_project}")
    if instance.team is not None:
        details.append(f"Team: {instance.team}")
    if instance.name is not None:
        details.append(f"Name: {instance.name}")
    if instance.priority is not None:
        details.append(f"Priority: {instance.priority}")
    if instance.description is not None:
        details.append(f"Description: {instance.description}")
    
    return f"Meetings and Tasks {page_id}:\n" + "\n".join(details)


async def list_meetings_and_taskss(
    client: NotionClient,
    limit: Optional[int] = 10,
    filter_by_task_progress_contains: Optional[str] = None,
    filter_by_name_contains: Optional[str] = None,
    filter_by_priority: Optional[str] = None,
    filter_by_description_contains: Optional[str] = None,
) -> str:
    """List Meetings and Taskss with optional filtering."""
    
    # Build filters
    filters = []
    if filter_by_task_progress_contains is not None:
        filters.append(MeetingsAndTasks.filter_by_task_progress_contains(filter_by_task_progress_contains))
    if filter_by_name_contains is not None:
        filters.append(MeetingsAndTasks.filter_by_name_contains(filter_by_name_contains))
    if filter_by_priority is not None:
        filters.append(MeetingsAndTasks.filter_by_priority(filter_by_priority))
    if filter_by_description_contains is not None:
        filters.append(MeetingsAndTasks.filter_by_description_contains(filter_by_description_contains))
    
    # Combine filters
    filter_condition = None
    if filters:
        if len(filters) == 1:
            filter_condition = filters[0]
        else:
            filter_condition = FilterBuilder().and_(*filters)
    
    # Sort by last edited time (newest first)
    sorts = [SortBuilder().last_edited_time().desc()]
    
    instances = await MeetingsAndTasks.list(
        client=client,
        filter_condition=filter_condition,
        sorts=sorts,
        limit=limit
    )
    
    if not instances:
        return "No Meetings and Taskss found"
    
    # Format results
    results = []
    for instance in instances:
        title = instance.name or "Untitled"
        break
        results.append(f"• {title}")
    
    return f"Found {len(instances)} Meetings and Taskss:\n" + "\n".join(results)


# Property-specific tools

async def add_meetings_and_tasks_blocking(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Blocking for a Meetings and Tasks."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    current_relations = instance.get_blocking() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_blocking(current_relations)
        await instance.update(page_id)
        return f"Added relation to Blocking for Meetings and Tasks {page_id}"
    else:
        return f"Relation already exists in Blocking for Meetings and Tasks {page_id}"


async def remove_meetings_and_tasks_blocking(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Blocking for a Meetings and Tasks."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    current_relations = instance.get_blocking() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_blocking(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Blocking for Meetings and Tasks {page_id}"
    else:
        return f"Relation not found in Blocking for Meetings and Tasks {page_id}"


async def add_meetings_and_tasks_parent_task(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Parent task for a Meetings and Tasks."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    current_relations = instance.get_parent_task() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_parent_task(current_relations)
        await instance.update(page_id)
        return f"Added relation to Parent task for Meetings and Tasks {page_id}"
    else:
        return f"Relation already exists in Parent task for Meetings and Tasks {page_id}"


async def remove_meetings_and_tasks_parent_task(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Parent task for a Meetings and Tasks."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    current_relations = instance.get_parent_task() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_parent_task(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Parent task for Meetings and Tasks {page_id}"
    else:
        return f"Relation not found in Parent task for Meetings and Tasks {page_id}"


async def add_meetings_and_tasks_blocked_by(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Blocked by for a Meetings and Tasks."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    current_relations = instance.get_blocked_by() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_blocked_by(current_relations)
        await instance.update(page_id)
        return f"Added relation to Blocked by for Meetings and Tasks {page_id}"
    else:
        return f"Relation already exists in Blocked by for Meetings and Tasks {page_id}"


async def remove_meetings_and_tasks_blocked_by(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Blocked by for a Meetings and Tasks."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    current_relations = instance.get_blocked_by() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_blocked_by(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Blocked by for Meetings and Tasks {page_id}"
    else:
        return f"Relation not found in Blocked by for Meetings and Tasks {page_id}"


async def add_meetings_and_tasks_sub_task(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Sub-task for a Meetings and Tasks."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    current_relations = instance.get_sub_task() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_sub_task(current_relations)
        await instance.update(page_id)
        return f"Added relation to Sub-task for Meetings and Tasks {page_id}"
    else:
        return f"Relation already exists in Sub-task for Meetings and Tasks {page_id}"


async def remove_meetings_and_tasks_sub_task(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Sub-task for a Meetings and Tasks."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    current_relations = instance.get_sub_task() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_sub_task(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Sub-task for Meetings and Tasks {page_id}"
    else:
        return f"Relation not found in Sub-task for Meetings and Tasks {page_id}"


async def add_meetings_and_tasks_event_project(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Event/Project for a Meetings and Tasks."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    current_relations = instance.get_event_project() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_event_project(current_relations)
        await instance.update(page_id)
        return f"Added relation to Event/Project for Meetings and Tasks {page_id}"
    else:
        return f"Relation already exists in Event/Project for Meetings and Tasks {page_id}"


async def remove_meetings_and_tasks_event_project(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Event/Project for a Meetings and Tasks."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    current_relations = instance.get_event_project() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_event_project(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Event/Project for Meetings and Tasks {page_id}"
    else:
        return f"Relation not found in Event/Project for Meetings and Tasks {page_id}"


async def add_meetings_and_tasks_team(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Add a relation to Team for a Meetings and Tasks."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    current_relations = instance.get_team() or []
    
    if related_page_id not in current_relations:
        current_relations.append(related_page_id)
        instance.set_team(current_relations)
        await instance.update(page_id)
        return f"Added relation to Team for Meetings and Tasks {page_id}"
    else:
        return f"Relation already exists in Team for Meetings and Tasks {page_id}"


async def remove_meetings_and_tasks_team(
    client: NotionClient,
    page_id: str,
    related_page_id: str
) -> str:
    """Remove a relation from Team for a Meetings and Tasks."""
    
    instance = await MeetingsAndTasks.get(client, page_id)
    current_relations = instance.get_team() or []
    
    if related_page_id in current_relations:
        current_relations.remove(related_page_id)
        instance.set_team(current_relations)
        await instance.update(page_id)
        return f"Removed relation from Team for Meetings and Tasks {page_id}"
    else:
        return f"Relation not found in Team for Meetings and Tasks {page_id}"


async def set_meetings_and_tasks_priority(
    client: NotionClient,
    page_id: str,
    priority: str
) -> str:
    """Set Priority for a Meetings and Tasks."""
    
    # Validate the value
    valid_options = ["Low", "Medium", "High"]
    if priority not in valid_options:
        return f"Invalid Priority. Valid options: {', '.join(valid_options)}"
    
    instance = await MeetingsAndTasks.get(client, page_id)
    instance.set_priority(priority)
    await instance.update(page_id)
    
    return f"Set Priority to '{priority}' for Meetings and Tasks {page_id}"



# LLMgine Tool Definitions

TOOLS = [
    Tool(
        name="create_meetings_and_tasks",
        description="Create a new Meetings and Tasks",
        parameters=[
            Parameter(
                name="name",
                description="Name",
                type="string",
                required=True
            ),
            Parameter(
                name="status",
                description="Status",
                type="string",
                required=False
            ),
            Parameter(
                name="blocking",
                description="Blocking",
                type="array",
                required=False
            ),
            Parameter(
                name="due_dates",
                description="Due Dates",
                type="string",
                required=False
            ),
            Parameter(
                name="parent_task",
                description="Parent task",
                type="array",
                required=False
            ),
            Parameter(
                name="blocked_by",
                description="Blocked by",
                type="array",
                required=False
            ),
            Parameter(
                name="sub_task",
                description="Sub-task",
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
                name="task_progress",
                description="Task Progress",
                type="string",
                required=False
            ),
            Parameter(
                name="event_project",
                description="Event/Project",
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
        ],
        function=create_meetings_and_tasks,
        is_async=True
    ),
    Tool(
        name="update_meetings_and_tasks",
        description="Update an existing Meetings and Tasks",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to update",
                type="str",
                required=True
            ),
            Parameter(
                name="status",
                description="Status",
                type="string",
                required=False
            ),
            Parameter(
                name="blocking",
                description="Blocking",
                type="array",
                required=False
            ),
            Parameter(
                name="due_dates",
                description="Due Dates",
                type="string",
                required=False
            ),
            Parameter(
                name="parent_task",
                description="Parent task",
                type="array",
                required=False
            ),
            Parameter(
                name="blocked_by",
                description="Blocked by",
                type="array",
                required=False
            ),
            Parameter(
                name="sub_task",
                description="Sub-task",
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
                name="task_progress",
                description="Task Progress",
                type="string",
                required=False
            ),
            Parameter(
                name="event_project",
                description="Event/Project",
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
                name="name",
                description="Name",
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
        ],
        function=update_meetings_and_tasks,
        is_async=True
    ),
    Tool(
        name="get_meetings_and_tasks",
        description="Get a Meetings and Tasks by ID",
        parameters=[
            Parameter(
                name="page_id",
                description="ID of the page to retrieve",
                type="str",
                required=True
            )
        ],
        function=get_meetings_and_tasks,
        is_async=True
    ),
    Tool(
        name="list_meetings_and_taskss",
        description="List Meetings and Taskss with optional filtering",
        parameters=[
            Parameter(
                name="limit",
                description="Maximum number of results to return",
                type="int",
                required=False
            ),
            Parameter(
                name="filter_by_task_progress_contains",
                description="Filter by Task Progress containing text",
                type="str",
                required=False
            ),
            Parameter(
                name="filter_by_name_contains",
                description="Filter by Name containing text",
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
        ],
        function=list_meetings_and_taskss,
        is_async=True
    ),
    Tool(
        name="add_meetings_and_tasks_blocking",
        description="Add a relation to Blocking for a Meetings and Tasks",
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
        function=add_meetings_and_tasks_blocking,
        is_async=True
    ),
    Tool(
        name="remove_meetings_and_tasks_blocking",
        description="Remove a relation from Blocking for a Meetings and Tasks",
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
        function=remove_meetings_and_tasks_blocking,
        is_async=True
    ),
    Tool(
        name="add_meetings_and_tasks_parent_task",
        description="Add a relation to Parent task for a Meetings and Tasks",
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
        function=add_meetings_and_tasks_parent_task,
        is_async=True
    ),
    Tool(
        name="remove_meetings_and_tasks_parent_task",
        description="Remove a relation from Parent task for a Meetings and Tasks",
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
        function=remove_meetings_and_tasks_parent_task,
        is_async=True
    ),
    Tool(
        name="add_meetings_and_tasks_blocked_by",
        description="Add a relation to Blocked by for a Meetings and Tasks",
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
        function=add_meetings_and_tasks_blocked_by,
        is_async=True
    ),
    Tool(
        name="remove_meetings_and_tasks_blocked_by",
        description="Remove a relation from Blocked by for a Meetings and Tasks",
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
        function=remove_meetings_and_tasks_blocked_by,
        is_async=True
    ),
    Tool(
        name="add_meetings_and_tasks_sub_task",
        description="Add a relation to Sub-task for a Meetings and Tasks",
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
        function=add_meetings_and_tasks_sub_task,
        is_async=True
    ),
    Tool(
        name="remove_meetings_and_tasks_sub_task",
        description="Remove a relation from Sub-task for a Meetings and Tasks",
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
        function=remove_meetings_and_tasks_sub_task,
        is_async=True
    ),
    Tool(
        name="add_meetings_and_tasks_event_project",
        description="Add a relation to Event/Project for a Meetings and Tasks",
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
        function=add_meetings_and_tasks_event_project,
        is_async=True
    ),
    Tool(
        name="remove_meetings_and_tasks_event_project",
        description="Remove a relation from Event/Project for a Meetings and Tasks",
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
        function=remove_meetings_and_tasks_event_project,
        is_async=True
    ),
    Tool(
        name="add_meetings_and_tasks_team",
        description="Add a relation to Team for a Meetings and Tasks",
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
        function=add_meetings_and_tasks_team,
        is_async=True
    ),
    Tool(
        name="remove_meetings_and_tasks_team",
        description="Remove a relation from Team for a Meetings and Tasks",
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
        function=remove_meetings_and_tasks_team,
        is_async=True
    ),
    Tool(
        name="set_meetings_and_tasks_priority",
        description="Set Priority for a Meetings and Tasks",
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
        function=set_meetings_and_tasks_priority,
        is_async=True
    ),
]