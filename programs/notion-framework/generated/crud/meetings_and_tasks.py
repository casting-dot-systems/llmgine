"""Generated CRUD functions for Meetings and Tasks database."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from notion_framework.client.client import NotionClient
from notion_framework.types.filters import FilterBuilder
from notion_framework.types.sorts import SortBuilder

from ..types import (
    MeetingsAndTasksID,
    MeetingsAndTasks_Priority,
)


# CRUD Functions for Meetings and Tasks

async def create_meetings_and_tasks(
    client: NotionClient,
    data: Dict[str, Any]
) -> MeetingsAndTasksID:
    """Create a new Meetings and Tasks entry.
    
    Args:
        client: Notion client instance
        data: Dictionary containing the properties to set
        
    Returns:
        ID of the created page
    """
    properties = {}
    
    # Convert data to Notion format
    if "status" in data:
        value = data["status"]
        # Convert based on property type
        # Generic handling for other types
        properties["Status"] = {
            "status": value
        }
    if "blocking" in data:
        value = data["blocking"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Blocking"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "due_dates" in data:
        value = data["due_dates"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Due Dates"] = {"date": {"start": value}}
    if "parent_task" in data:
        value = data["parent_task"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Parent task"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "blocked_by" in data:
        value = data["blocked_by"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Blocked by"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "sub_task" in data:
        value = data["sub_task"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Sub-task"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "in_charge" in data:
        value = data["in_charge"]
        # Convert based on property type
        # Generic handling for other types
        properties["In Charge"] = {
            "people": value
        }
    if "task_progress" in data:
        value = data["task_progress"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Task Progress"] = {"rich_text": [{"text": {"content": value}}]}
    if "event_project" in data:
        value = data["event_project"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Event/Project"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "team" in data:
        value = data["team"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Team"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "name" in data:
        value = data["name"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Name"] = {"title": [{"text": {"content": value}}]}
    if "priority" in data:
        value = data["priority"]
        # Convert based on property type
        if isinstance(value, (str, MeetingsAndTasks_Priority)):
            properties["Priority"] = {"select": {"name": str(value)}}
    if "description" in data:
        value = data["description"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Description"] = {"rich_text": [{"text": {"content": value}}]}
    
    # Create the page
    response = await client.create_page(
        database_id="ed8ba37a-719a-47d7-a796-c2d373c794b9",
        properties=properties
    )
    
    return MeetingsAndTasksID(response["id"])


async def read_meetings_and_tasks(
    client: NotionClient,
    page_id: MeetingsAndTasksID
) -> Dict[str, Any]:
    """Read a Meetings and Tasks entry by ID.
    
    Args:
        client: Notion client instance
        page_id: ID of the page to read
        
    Returns:
        Dictionary containing the page properties
    """
    response = await client.get_page(str(page_id))
    
    # Extract properties
    data = {}
    properties = response.get("properties", {})
    
    # Extract Due Date
    if "Due Date" in properties:
        prop_data = properties["Due Date"]
        data["due_date"] = prop_data.get("formula")
    # Extract Status
    if "Status" in properties:
        prop_data = properties["Status"]
        data["status"] = prop_data.get("status")
    # Extract Blocking
    if "Blocking" in properties:
        prop_data = properties["Blocking"]
        if prop_data.get("relation"):
            data["blocking"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Due Dates
    if "Due Dates" in properties:
        prop_data = properties["Due Dates"]
        if prop_data.get("date") and prop_data["date"].get("start"):
            data["due_dates"] = prop_data["date"]["start"]
    # Extract Parent task
    if "Parent task" in properties:
        prop_data = properties["Parent task"]
        if prop_data.get("relation"):
            data["parent_task"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Blocked by
    if "Blocked by" in properties:
        prop_data = properties["Blocked by"]
        if prop_data.get("relation"):
            data["blocked_by"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Last edited time
    if "Last edited time" in properties:
        prop_data = properties["Last edited time"]
        data["last_edited_time"] = prop_data.get("last_edited_time")
    # Extract Sub-task
    if "Sub-task" in properties:
        prop_data = properties["Sub-task"]
        if prop_data.get("relation"):
            data["sub_task"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract In Charge
    if "In Charge" in properties:
        prop_data = properties["In Charge"]
        data["in_charge"] = prop_data.get("people")
    # Extract Is Due 
    if "Is Due " in properties:
        prop_data = properties["Is Due "]
        data["is_due_"] = prop_data.get("formula")
    # Extract Task Progress
    if "Task Progress" in properties:
        prop_data = properties["Task Progress"]
        if prop_data.get("rich_text"):
            data["task_progress"] = "".join(
                text.get("plain_text", "") for text in prop_data["rich_text"]
            )
    # Extract Last edited by
    if "Last edited by" in properties:
        prop_data = properties["Last edited by"]
        data["last_edited_by"] = prop_data.get("last_edited_by")
    # Extract Event/Project
    if "Event/Project" in properties:
        prop_data = properties["Event/Project"]
        if prop_data.get("relation"):
            data["event_project"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Team
    if "Team" in properties:
        prop_data = properties["Team"]
        if prop_data.get("relation"):
            data["team"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Name
    if "Name" in properties:
        prop_data = properties["Name"]
        if prop_data.get("title"):
            data["name"] = "".join(
                text.get("plain_text", "") for text in prop_data["title"]
            )
    # Extract Priority
    if "Priority" in properties:
        prop_data = properties["Priority"]
        if prop_data.get("select"):
            data["priority"] = MeetingsAndTasks_Priority(
                prop_data["select"]["name"]
            )
    # Extract Description
    if "Description" in properties:
        prop_data = properties["Description"]
        if prop_data.get("rich_text"):
            data["description"] = "".join(
                text.get("plain_text", "") for text in prop_data["rich_text"]
            )
    
    return data


async def update_meetings_and_tasks(
    client: NotionClient,
    page_id: MeetingsAndTasksID,
    data: Dict[str, Any]
) -> MeetingsAndTasksID:
    """Update a Meetings and Tasks entry.
    
    Args:
        client: Notion client instance
        page_id: ID of the page to update
        data: Dictionary containing the properties to update
        
    Returns:
        ID of the updated page
    """
    properties = {}
    
    # Convert data to Notion format (same logic as create)
    if "status" in data:
        value = data["status"]
        # Convert based on property type
        # Generic handling for other types
        properties["Status"] = {
            "status": value
        }
    if "blocking" in data:
        value = data["blocking"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Blocking"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "due_dates" in data:
        value = data["due_dates"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Due Dates"] = {"date": {"start": value}}
    if "parent_task" in data:
        value = data["parent_task"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Parent task"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "blocked_by" in data:
        value = data["blocked_by"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Blocked by"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "sub_task" in data:
        value = data["sub_task"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Sub-task"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "in_charge" in data:
        value = data["in_charge"]
        # Convert based on property type
        # Generic handling for other types
        properties["In Charge"] = {
            "people": value
        }
    if "task_progress" in data:
        value = data["task_progress"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Task Progress"] = {"rich_text": [{"text": {"content": value}}]}
    if "event_project" in data:
        value = data["event_project"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Event/Project"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "team" in data:
        value = data["team"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Team"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "name" in data:
        value = data["name"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Name"] = {"title": [{"text": {"content": value}}]}
    if "priority" in data:
        value = data["priority"]
        # Convert based on property type
        if isinstance(value, (str, MeetingsAndTasks_Priority)):
            properties["Priority"] = {"select": {"name": str(value)}}
    if "description" in data:
        value = data["description"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Description"] = {"rich_text": [{"text": {"content": value}}]}
    
    # Update the page
    await client.update_page(str(page_id), properties=properties)
    
    return page_id


async def delete_meetings_and_tasks(
    client: NotionClient,
    page_id: MeetingsAndTasksID
) -> MeetingsAndTasksID:
    """Delete (archive) a Meetings and Tasks entry.
    
    Args:
        client: Notion client instance
        page_id: ID of the page to delete
        
    Returns:
        ID of the deleted page
    """
    await client.update_page(str(page_id), archived=True)
    return page_id


async def list_meetings_and_taskss(
    client: NotionClient,
    limit: int = 100,
    filter_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """List Meetings and Tasks entries.
    
    Args:
        client: Notion client instance
        limit: Maximum number of entries to return
        filter_data: Optional filter criteria
        
    Returns:
        List of dictionaries containing the page properties
    """
    # Build query
    query_data = {
        "page_size": limit
    }
    
    if filter_data:
        query_data["filter"] = filter_data
    
    # Query the database
    response = await client.query_database("ed8ba37a-719a-47d7-a796-c2d373c794b9", **query_data)
    
    # Extract data from each page
    results = []
    for page in response.get("results", []):
        page_data = {"id": MeetingsAndTasksID(page["id"])}
        properties = page.get("properties", {})
        
        # Extract Due Date
        if "Due Date" in properties:
            prop_data = properties["Due Date"]
            page_data["due_date"] = prop_data.get("formula")
        # Extract Status
        if "Status" in properties:
            prop_data = properties["Status"]
            page_data["status"] = prop_data.get("status")
        # Extract Blocking
        if "Blocking" in properties:
            prop_data = properties["Blocking"]
            if prop_data.get("relation"):
                page_data["blocking"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Due Dates
        if "Due Dates" in properties:
            prop_data = properties["Due Dates"]
            if prop_data.get("date") and prop_data["date"].get("start"):
                page_data["due_dates"] = prop_data["date"]["start"]
        # Extract Parent task
        if "Parent task" in properties:
            prop_data = properties["Parent task"]
            if prop_data.get("relation"):
                page_data["parent_task"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Blocked by
        if "Blocked by" in properties:
            prop_data = properties["Blocked by"]
            if prop_data.get("relation"):
                page_data["blocked_by"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Last edited time
        if "Last edited time" in properties:
            prop_data = properties["Last edited time"]
            page_data["last_edited_time"] = prop_data.get("last_edited_time")
        # Extract Sub-task
        if "Sub-task" in properties:
            prop_data = properties["Sub-task"]
            if prop_data.get("relation"):
                page_data["sub_task"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract In Charge
        if "In Charge" in properties:
            prop_data = properties["In Charge"]
            page_data["in_charge"] = prop_data.get("people")
        # Extract Is Due 
        if "Is Due " in properties:
            prop_data = properties["Is Due "]
            page_data["is_due_"] = prop_data.get("formula")
        # Extract Task Progress
        if "Task Progress" in properties:
            prop_data = properties["Task Progress"]
            if prop_data.get("rich_text"):
                page_data["task_progress"] = "".join(
                    text.get("plain_text", "") for text in prop_data["rich_text"]
                )
        # Extract Last edited by
        if "Last edited by" in properties:
            prop_data = properties["Last edited by"]
            page_data["last_edited_by"] = prop_data.get("last_edited_by")
        # Extract Event/Project
        if "Event/Project" in properties:
            prop_data = properties["Event/Project"]
            if prop_data.get("relation"):
                page_data["event_project"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Team
        if "Team" in properties:
            prop_data = properties["Team"]
            if prop_data.get("relation"):
                page_data["team"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Name
        if "Name" in properties:
            prop_data = properties["Name"]
            if prop_data.get("title"):
                page_data["name"] = "".join(
                    text.get("plain_text", "") for text in prop_data["title"]
                )
        # Extract Priority
        if "Priority" in properties:
            prop_data = properties["Priority"]
            if prop_data.get("select"):
                page_data["priority"] = MeetingsAndTasks_Priority(
                    prop_data["select"]["name"]
                )
        # Extract Description
        if "Description" in properties:
            prop_data = properties["Description"]
            if prop_data.get("rich_text"):
                page_data["description"] = "".join(
                    text.get("plain_text", "") for text in prop_data["rich_text"]
                )
        
        results.append(page_data)
    
    return results


# Test Functions

async def test_meetings_and_tasks_crud():
    """Test CRUD operations for Meetings and Tasks."""
    import os
    from notion_framework.client.client import NotionClient
    
    # Initialize client
    token = os.getenv("NOTION_TOKEN")
    if not token:
        print("❌ NOTION_TOKEN environment variable is required for testing")
        return
    
    client = NotionClient(token)
    
    try:
        print("🧪 Testing Meetings and Tasks CRUD operations...")
        
        # Test data
        test_data = {
            "name": "Test Meetings and Tasks Entry",
        }
        
        # Test CREATE
        print("  ✅ Testing CREATE...")
        page_id = await create_meetings_and_tasks(client, test_data)
        print(f"     Created page: {page_id}")
        
        # Test READ
        print("  ✅ Testing READ...")
        data = await read_meetings_and_tasks(client, page_id)
        print(f"     Read data: {data}")
        
        # Test UPDATE
        print("  ✅ Testing UPDATE...")
        update_data = {
            "name": "Updated Test Entry",
        }
        await update_meetings_and_tasks(client, page_id, update_data)
        print("     Updated page")
        
        # Test LIST
        print("  ✅ Testing LIST...")
        results = await list_meetings_and_taskss(client, limit=5)
        print(f"     Found {len(results)} entries")
        
        # Test DELETE
        print("  ✅ Testing DELETE...")
        await delete_meetings_and_tasks(client, page_id)
        print("     Deleted page")
        
        print("✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_meetings_and_tasks_crud())