"""Generated CRUD functions for Teams database."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from notion_framework.client.client import NotionClient
from notion_framework.types.filters import FilterBuilder
from notion_framework.types.sorts import SortBuilder

from ..types import (
    TeamsID,
)


# CRUD Functions for Teams

async def create_teams(
    client: NotionClient,
    data: Dict[str, Any]
) -> TeamsID:
    """Create a new Teams entry.
    
    Args:
        client: Notion client instance
        data: Dictionary containing the properties to set
        
    Returns:
        ID of the created page
    """
    properties = {}
    
    # Convert data to Notion format
    if "__events_projects" in data:
        value = data["__events_projects"]
        # Convert based on property type
        if isinstance(value, list):
            properties["💥 Events/Projects"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "cover" in data:
        value = data["cover"]
        # Convert based on property type
        # Generic handling for other types
        properties["Cover"] = {
            "files": value
        }
    if "person" in data:
        value = data["person"]
        # Convert based on property type
        # Generic handling for other types
        properties["Person"] = {
            "people": value
        }
    if "committee" in data:
        value = data["committee"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Committee"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "document" in data:
        value = data["document"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Document"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "name" in data:
        value = data["name"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Name"] = {"title": [{"text": {"content": value}}]}
    
    # Create the page
    response = await client.create_page(
        database_id="139594e5-2bd9-47af-93ca-bb72a35742d2",
        properties=properties
    )
    
    return TeamsID(response["id"])


async def read_teams(
    client: NotionClient,
    page_id: TeamsID
) -> Dict[str, Any]:
    """Read a Teams entry by ID.
    
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
    
    # Extract 💥 Events/Projects
    if "💥 Events/Projects" in properties:
        prop_data = properties["💥 Events/Projects"]
        if prop_data.get("relation"):
            data["__events_projects"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Cover
    if "Cover" in properties:
        prop_data = properties["Cover"]
        data["cover"] = prop_data.get("files")
    # Extract Person
    if "Person" in properties:
        prop_data = properties["Person"]
        data["person"] = prop_data.get("people")
    # Extract Committee
    if "Committee" in properties:
        prop_data = properties["Committee"]
        if prop_data.get("relation"):
            data["committee"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Document
    if "Document" in properties:
        prop_data = properties["Document"]
        if prop_data.get("relation"):
            data["document"] = [
                rel["id"] for rel in prop_data["relation"]
            ]
    # Extract Name
    if "Name" in properties:
        prop_data = properties["Name"]
        if prop_data.get("title"):
            data["name"] = "".join(
                text.get("plain_text", "") for text in prop_data["title"]
            )
    
    return data


async def update_teams(
    client: NotionClient,
    page_id: TeamsID,
    data: Dict[str, Any]
) -> TeamsID:
    """Update a Teams entry.
    
    Args:
        client: Notion client instance
        page_id: ID of the page to update
        data: Dictionary containing the properties to update
        
    Returns:
        ID of the updated page
    """
    properties = {}
    
    # Convert data to Notion format (same logic as create)
    if "__events_projects" in data:
        value = data["__events_projects"]
        # Convert based on property type
        if isinstance(value, list):
            properties["💥 Events/Projects"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "cover" in data:
        value = data["cover"]
        # Convert based on property type
        # Generic handling for other types
        properties["Cover"] = {
            "files": value
        }
    if "person" in data:
        value = data["person"]
        # Convert based on property type
        # Generic handling for other types
        properties["Person"] = {
            "people": value
        }
    if "committee" in data:
        value = data["committee"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Committee"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "document" in data:
        value = data["document"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Document"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "name" in data:
        value = data["name"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Name"] = {"title": [{"text": {"content": value}}]}
    
    # Update the page
    await client.update_page(str(page_id), properties=properties)
    
    return page_id


async def delete_teams(
    client: NotionClient,
    page_id: TeamsID
) -> TeamsID:
    """Delete (archive) a Teams entry.
    
    Args:
        client: Notion client instance
        page_id: ID of the page to delete
        
    Returns:
        ID of the deleted page
    """
    await client.update_page(str(page_id), archived=True)
    return page_id


async def list_teamss(
    client: NotionClient,
    limit: int = 100,
    filter_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """List Teams entries.
    
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
    response = await client.query_database("139594e5-2bd9-47af-93ca-bb72a35742d2", **query_data)
    
    # Extract data from each page
    results = []
    for page in response.get("results", []):
        page_data = {"id": TeamsID(page["id"])}
        properties = page.get("properties", {})
        
        # Extract 💥 Events/Projects
        if "💥 Events/Projects" in properties:
            prop_data = properties["💥 Events/Projects"]
            if prop_data.get("relation"):
                page_data["__events_projects"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Cover
        if "Cover" in properties:
            prop_data = properties["Cover"]
            page_data["cover"] = prop_data.get("files")
        # Extract Person
        if "Person" in properties:
            prop_data = properties["Person"]
            page_data["person"] = prop_data.get("people")
        # Extract Committee
        if "Committee" in properties:
            prop_data = properties["Committee"]
            if prop_data.get("relation"):
                page_data["committee"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Document
        if "Document" in properties:
            prop_data = properties["Document"]
            if prop_data.get("relation"):
                page_data["document"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
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

async def test_teams_crud():
    """Test CRUD operations for Teams."""
    import os
    from notion_framework.client.client import NotionClient
    
    # Initialize client
    token = os.getenv("NOTION_TOKEN")
    if not token:
        print("❌ NOTION_TOKEN environment variable is required for testing")
        return
    
    client = NotionClient(token)
    
    try:
        print("🧪 Testing Teams CRUD operations...")
        
        # Test data
        test_data = {
            "name": "Test Teams Entry",
        }
        
        # Test CREATE
        print("  ✅ Testing CREATE...")
        page_id = await create_teams(client, test_data)
        print(f"     Created page: {page_id}")
        
        # Test READ
        print("  ✅ Testing READ...")
        data = await read_teams(client, page_id)
        print(f"     Read data: {data}")
        
        # Test UPDATE
        print("  ✅ Testing UPDATE...")
        update_data = {
            "name": "Updated Test Entry",
        }
        await update_teams(client, page_id, update_data)
        print("     Updated page")
        
        # Test LIST
        print("  ✅ Testing LIST...")
        results = await list_teamss(client, limit=5)
        print(f"     Found {len(results)} entries")
        
        # Test DELETE
        print("  ✅ Testing DELETE...")
        await delete_teams(client, page_id)
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
    asyncio.run(test_teams_crud())