"""Generated CRUD functions for Events/Projects database."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from notion_framework.client.client import NotionClient
from notion_framework.types.filters import FilterBuilder
from notion_framework.types.sorts import SortBuilder

from ..types import (
    EventsProjectsID,
    EventsProjects_Type,
    EventsProjects_Progress,
    EventsProjects_Priority,
)


# CRUD Functions for Events/Projects

async def create_events_projects(
    client: NotionClient,
    data: Dict[str, Any]
) -> EventsProjectsID:
    """Create a new Events/Projects entry.
    
    Args:
        client: Notion client instance
        data: Dictionary containing the properties to set
        
    Returns:
        ID of the created page
    """
    properties = {}
    
    # Convert data to Notion format
    if "parent_item" in data:
        value = data["parent_item"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Parent item"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "type" in data:
        value = data["type"]
        # Convert based on property type
        if isinstance(value, (str, EventsProjects_Type)):
            properties["Type"] = {"select": {"name": str(value)}}
    if "owner" in data:
        value = data["owner"]
        # Convert based on property type
        # Generic handling for other types
        properties["Owner"] = {
            "people": value
        }
    if "sub_item" in data:
        value = data["sub_item"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Sub-item"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "allocated" in data:
        value = data["allocated"]
        # Convert based on property type
        # Generic handling for other types
        properties["Allocated"] = {
            "people": value
        }
    if "team" in data:
        value = data["team"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Team"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "text" in data:
        value = data["text"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Text"] = {"rich_text": [{"text": {"content": value}}]}
    if "progress" in data:
        value = data["progress"]
        # Convert based on property type
        if isinstance(value, (str, EventsProjects_Progress)):
            properties["Progress"] = {"select": {"name": str(value)}}
    if "priority" in data:
        value = data["priority"]
        # Convert based on property type
        if isinstance(value, (str, EventsProjects_Priority)):
            properties["Priority"] = {"select": {"name": str(value)}}
    if "description" in data:
        value = data["description"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Description"] = {"rich_text": [{"text": {"content": value}}]}
    if "due_date_s_" in data:
        value = data["due_date_s_"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Due Date(s)"] = {"date": {"start": value}}
    if "documents" in data:
        value = data["documents"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Documents"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "tasks" in data:
        value = data["tasks"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Tasks"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "location" in data:
        value = data["location"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Location"] = {"rich_text": [{"text": {"content": value}}]}
    if "name" in data:
        value = data["name"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Name"] = {"title": [{"text": {"content": value}}]}
    
    # Create the page
    response = await client.create_page(
        database_id="918affd4-ce0d-4b8e-b760-4d972fd24826",
        properties=properties
    )
    
    return EventsProjectsID(response["id"])


async def read_events_projects(
    client: NotionClient,
    page_id: EventsProjectsID
) -> Dict[str, Any]:
    """Read a Events/Projects entry by ID.
    
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
    
    # Extract Parent item
    if "Parent item" in properties:
        prop_data = properties["Parent item"]
        if prop_data.get("relation"):
            data["parent_item"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Type
    if "Type" in properties:
        prop_data = properties["Type"]
        if prop_data.get("select"):
            data["type"] = EventsProjects_Type(
                prop_data["select"]["name"]
            )
    # Extract Owner
    if "Owner" in properties:
        prop_data = properties["Owner"]
        data["owner"] = prop_data.get("people")
    # Extract Sub-item
    if "Sub-item" in properties:
        prop_data = properties["Sub-item"]
        if prop_data.get("relation"):
            data["sub_item"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Allocated
    if "Allocated" in properties:
        prop_data = properties["Allocated"]
        data["allocated"] = prop_data.get("people")
    # Extract Team
    if "Team" in properties:
        prop_data = properties["Team"]
        if prop_data.get("relation"):
            data["team"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Text
    if "Text" in properties:
        prop_data = properties["Text"]
        if prop_data.get("rich_text"):
            data["text"] = "".join(
                text.get("plain_text", "") for text in prop_data["rich_text"]
            )
    # Extract Progress
    if "Progress" in properties:
        prop_data = properties["Progress"]
        if prop_data.get("select"):
            data["progress"] = EventsProjects_Progress(
                prop_data["select"]["name"]
            )
    # Extract Priority
    if "Priority" in properties:
        prop_data = properties["Priority"]
        if prop_data.get("select"):
            data["priority"] = EventsProjects_Priority(
                prop_data["select"]["name"]
            )
    # Extract Description
    if "Description" in properties:
        prop_data = properties["Description"]
        if prop_data.get("rich_text"):
            data["description"] = "".join(
                text.get("plain_text", "") for text in prop_data["rich_text"]
            )
    # Extract Due Date(s)
    if "Due Date(s)" in properties:
        prop_data = properties["Due Date(s)"]
        if prop_data.get("date") and prop_data["date"].get("start"):
            data["due_date_s_"] = prop_data["date"]["start"]
    # Extract Documents
    if "Documents" in properties:
        prop_data = properties["Documents"]
        if prop_data.get("relation"):
            data["documents"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Tasks
    if "Tasks" in properties:
        prop_data = properties["Tasks"]
        if prop_data.get("relation"):
            data["tasks"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Location
    if "Location" in properties:
        prop_data = properties["Location"]
        if prop_data.get("rich_text"):
            data["location"] = "".join(
                text.get("plain_text", "") for text in prop_data["rich_text"]
            )
    # Extract Name
    if "Name" in properties:
        prop_data = properties["Name"]
        if prop_data.get("title"):
            data["name"] = "".join(
                text.get("plain_text", "") for text in prop_data["title"]
            )
    
    return data


async def update_events_projects(
    client: NotionClient,
    page_id: EventsProjectsID,
    data: Dict[str, Any]
) -> EventsProjectsID:
    """Update a Events/Projects entry.
    
    Args:
        client: Notion client instance
        page_id: ID of the page to update
        data: Dictionary containing the properties to update
        
    Returns:
        ID of the updated page
    """
    properties = {}
    
    # Convert data to Notion format (same logic as create)
    if "parent_item" in data:
        value = data["parent_item"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Parent item"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "type" in data:
        value = data["type"]
        # Convert based on property type
        if isinstance(value, (str, EventsProjects_Type)):
            properties["Type"] = {"select": {"name": str(value)}}
    if "owner" in data:
        value = data["owner"]
        # Convert based on property type
        # Generic handling for other types
        properties["Owner"] = {
            "people": value
        }
    if "sub_item" in data:
        value = data["sub_item"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Sub-item"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "allocated" in data:
        value = data["allocated"]
        # Convert based on property type
        # Generic handling for other types
        properties["Allocated"] = {
            "people": value
        }
    if "team" in data:
        value = data["team"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Team"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "text" in data:
        value = data["text"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Text"] = {"rich_text": [{"text": {"content": value}}]}
    if "progress" in data:
        value = data["progress"]
        # Convert based on property type
        if isinstance(value, (str, EventsProjects_Progress)):
            properties["Progress"] = {"select": {"name": str(value)}}
    if "priority" in data:
        value = data["priority"]
        # Convert based on property type
        if isinstance(value, (str, EventsProjects_Priority)):
            properties["Priority"] = {"select": {"name": str(value)}}
    if "description" in data:
        value = data["description"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Description"] = {"rich_text": [{"text": {"content": value}}]}
    if "due_date_s_" in data:
        value = data["due_date_s_"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Due Date(s)"] = {"date": {"start": value}}
    if "documents" in data:
        value = data["documents"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Documents"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "tasks" in data:
        value = data["tasks"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Tasks"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "location" in data:
        value = data["location"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Location"] = {"rich_text": [{"text": {"content": value}}]}
    if "name" in data:
        value = data["name"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Name"] = {"title": [{"text": {"content": value}}]}
    
    # Update the page
    await client.update_page(str(page_id), properties=properties)
    
    return page_id


async def delete_events_projects(
    client: NotionClient,
    page_id: EventsProjectsID
) -> EventsProjectsID:
    """Delete (archive) a Events/Projects entry.
    
    Args:
        client: Notion client instance
        page_id: ID of the page to delete
        
    Returns:
        ID of the deleted page
    """
    await client.update_page(str(page_id), archived=True)
    return page_id


async def list_events_projectss(
    client: NotionClient,
    limit: int = 100,
    filter_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """List Events/Projects entries.
    
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
    response = await client.query_database("918affd4-ce0d-4b8e-b760-4d972fd24826", **query_data)
    
    # Extract data from each page
    results = []
    for page in response.get("results", []):
        page_data = {"id": EventsProjectsID(page["id"])}
        properties = page.get("properties", {})
        
        # Extract Parent item
        if "Parent item" in properties:
            prop_data = properties["Parent item"]
            if prop_data.get("relation"):
                page_data["parent_item"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Type
        if "Type" in properties:
            prop_data = properties["Type"]
            if prop_data.get("select"):
                page_data["type"] = EventsProjects_Type(
                    prop_data["select"]["name"]
                )
        # Extract Owner
        if "Owner" in properties:
            prop_data = properties["Owner"]
            page_data["owner"] = prop_data.get("people")
        # Extract Sub-item
        if "Sub-item" in properties:
            prop_data = properties["Sub-item"]
            if prop_data.get("relation"):
                page_data["sub_item"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Allocated
        if "Allocated" in properties:
            prop_data = properties["Allocated"]
            page_data["allocated"] = prop_data.get("people")
        # Extract Team
        if "Team" in properties:
            prop_data = properties["Team"]
            if prop_data.get("relation"):
                page_data["team"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Text
        if "Text" in properties:
            prop_data = properties["Text"]
            if prop_data.get("rich_text"):
                page_data["text"] = "".join(
                    text.get("plain_text", "") for text in prop_data["rich_text"]
                )
        # Extract Progress
        if "Progress" in properties:
            prop_data = properties["Progress"]
            if prop_data.get("select"):
                page_data["progress"] = EventsProjects_Progress(
                    prop_data["select"]["name"]
                )
        # Extract Priority
        if "Priority" in properties:
            prop_data = properties["Priority"]
            if prop_data.get("select"):
                page_data["priority"] = EventsProjects_Priority(
                    prop_data["select"]["name"]
                )
        # Extract Description
        if "Description" in properties:
            prop_data = properties["Description"]
            if prop_data.get("rich_text"):
                page_data["description"] = "".join(
                    text.get("plain_text", "") for text in prop_data["rich_text"]
                )
        # Extract Due Date(s)
        if "Due Date(s)" in properties:
            prop_data = properties["Due Date(s)"]
            if prop_data.get("date") and prop_data["date"].get("start"):
                page_data["due_date_s_"] = prop_data["date"]["start"]
        # Extract Documents
        if "Documents" in properties:
            prop_data = properties["Documents"]
            if prop_data.get("relation"):
                page_data["documents"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Tasks
        if "Tasks" in properties:
            prop_data = properties["Tasks"]
            if prop_data.get("relation"):
                page_data["tasks"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Location
        if "Location" in properties:
            prop_data = properties["Location"]
            if prop_data.get("rich_text"):
                page_data["location"] = "".join(
                    text.get("plain_text", "") for text in prop_data["rich_text"]
                )
        # Extract Name
        if "Name" in properties:
            prop_data = properties["Name"]
            if prop_data.get("title"):
                page_data["name"] = "".join(
                    text.get("plain_text", "") for text in prop_data["title"]
                )
        
        results.append(page_data)
    
    return results


# Test Functions

async def test_events_projects_crud():
    """Test CRUD operations for Events/Projects."""
    import os
    from notion_framework.client.client import NotionClient
    
    # Initialize client
    token = os.getenv("NOTION_TOKEN")
    if not token:
        print("❌ NOTION_TOKEN environment variable is required for testing")
        return
    
    client = NotionClient(token)
    
    try:
        print("🧪 Testing Events/Projects CRUD operations...")
        
        # Test data
        test_data = {
            "name": "Test Events/Projects Entry",
        }
        
        # Test CREATE
        print("  ✅ Testing CREATE...")
        page_id = await create_events_projects(client, test_data)
        print(f"     Created page: {page_id}")
        
        # Test READ
        print("  ✅ Testing READ...")
        data = await read_events_projects(client, page_id)
        print(f"     Read data: {data}")
        
        # Test UPDATE
        print("  ✅ Testing UPDATE...")
        update_data = {
            "name": "Updated Test Entry",
        }
        await update_events_projects(client, page_id, update_data)
        print("     Updated page")
        
        # Test LIST
        print("  ✅ Testing LIST...")
        results = await list_events_projectss(client, limit=5)
        print(f"     Found {len(results)} entries")
        
        # Test DELETE
        print("  ✅ Testing DELETE...")
        await delete_events_projects(client, page_id)
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
    asyncio.run(test_events_projects_crud())