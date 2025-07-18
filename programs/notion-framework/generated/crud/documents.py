"""Generated CRUD functions for Documents database."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from notion_framework.client.client import NotionClient
from notion_framework.types.filters import FilterBuilder
from notion_framework.types.sorts import SortBuilder

from generated.types import (
    DocumentsID,
)


# CRUD Functions for Documents


async def create_documents(client: NotionClient, data: Dict[str, Any]) -> DocumentsID:
    """Create a new Documents entry.

    Args:
        client: Notion client instance
        data: Dictionary containing the properties to set

    Returns:
        ID of the created page
    """
    properties = {}

    # Convert data to Notion format
    if "events_projects" in data:
        value = data["events_projects"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Events/Projects"] = {
                "relation": [{"id": str(page_id)} for page_id in value]
            }
    if "parent_item" in data:
        value = data["parent_item"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Parent item"] = {
                "relation": [{"id": str(page_id)} for page_id in value]
            }
    if "google_drive_file" in data:
        value = data["google_drive_file"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Google Drive File"] = {
                "relation": [{"id": str(page_id)} for page_id in value]
            }
    if "person" in data:
        value = data["person"]
        # Convert based on property type
        # Generic handling for other types
        properties["Person"] = {"people": value}
    if "contributors" in data:
        value = data["contributors"]
        # Convert based on property type
        # Generic handling for other types
        properties["Contributors"] = {"people": value}
    if "team" in data:
        value = data["team"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Team"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "pinned" in data:
        value = data["pinned"]
        # Convert based on property type
        if isinstance(value, bool):
            properties["Pinned"] = {"checkbox": value}
    if "owned_by" in data:
        value = data["owned_by"]
        # Convert based on property type
        # Generic handling for other types
        properties["Owned By"] = {"people": value}
    if "sub_item" in data:
        value = data["sub_item"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Sub-item"] = {
                "relation": [{"id": str(page_id)} for page_id in value]
            }
    if "name" in data:
        value = data["name"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Name"] = {"title": [{"text": {"content": value}}]}
    if "in_charge" in data:
        value = data["in_charge"]
        # Convert based on property type
        # Generic handling for other types
        properties["In Charge"] = {"people": value}
    if "status" in data:
        value = data["status"]
        # Convert based on property type
        # Generic handling for other types
        properties["Status"] = {"status": value}

    # Create the page
    response = await client.create_page(
        database_id="55909df8-1f56-40c4-9327-bab99b4f97f5", properties=properties
    )

    return DocumentsID(response["id"])


async def read_documents(client: NotionClient, page_id: DocumentsID) -> Dict[str, Any]:
    """Read a Documents entry by ID.

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

    # Extract Events/Projects
    if "Events/Projects" in properties:
        prop_data = properties["Events/Projects"]
        if prop_data.get("relation"):
            data["events_projects"] = [rel["id"] for rel in prop_data["relation"]]
    # Extract Parent item
    if "Parent item" in properties:
        prop_data = properties["Parent item"]
        if prop_data.get("relation"):
            data["parent_item"] = [rel["id"] for rel in prop_data["relation"]]
    # Extract Last edited by
    if "Last edited by" in properties:
        prop_data = properties["Last edited by"]
        data["last_edited_by"] = prop_data.get("last_edited_by")
    # Extract Google Drive File
    if "Google Drive File" in properties:
        prop_data = properties["Google Drive File"]
        if prop_data.get("relation"):
            data["google_drive_file"] = [rel["id"] for rel in prop_data["relation"]]
    # Extract Person
    if "Person" in properties:
        prop_data = properties["Person"]
        data["person"] = prop_data.get("people")
    # Extract Contributors
    if "Contributors" in properties:
        prop_data = properties["Contributors"]
        data["contributors"] = prop_data.get("people")
    # Extract Team
    if "Team" in properties:
        prop_data = properties["Team"]
        if prop_data.get("relation"):
            data["team"] = [rel["id"] for rel in prop_data["relation"]]
    # Extract Pinned
    if "Pinned" in properties:
        prop_data = properties["Pinned"]
        data["pinned"] = prop_data.get("checkbox", False)
    # Extract Owned By
    if "Owned By" in properties:
        prop_data = properties["Owned By"]
        data["owned_by"] = prop_data.get("people")
    # Extract Sub-item
    if "Sub-item" in properties:
        prop_data = properties["Sub-item"]
        if prop_data.get("relation"):
            data["sub_item"] = [rel["id"] for rel in prop_data["relation"]]
    # Extract Name
    if "Name" in properties:
        prop_data = properties["Name"]
        if prop_data.get("title"):
            data["name"] = "".join(
                text.get("plain_text", "") for text in prop_data["title"]
            )
    # Extract In Charge
    if "In Charge" in properties:
        prop_data = properties["In Charge"]
        data["in_charge"] = prop_data.get("people")
    # Extract Status
    if "Status" in properties:
        prop_data = properties["Status"]
        data["status"] = prop_data.get("status")

    return data


async def update_documents(
    client: NotionClient, page_id: DocumentsID, data: Dict[str, Any]
) -> DocumentsID:
    """Update a Documents entry.

    Args:
        client: Notion client instance
        page_id: ID of the page to update
        data: Dictionary containing the properties to update

    Returns:
        ID of the updated page
    """
    properties = {}

    # Convert data to Notion format (same logic as create)
    if "events_projects" in data:
        value = data["events_projects"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Events/Projects"] = {
                "relation": [{"id": str(page_id)} for page_id in value]
            }
    if "parent_item" in data:
        value = data["parent_item"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Parent item"] = {
                "relation": [{"id": str(page_id)} for page_id in value]
            }
    if "google_drive_file" in data:
        value = data["google_drive_file"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Google Drive File"] = {
                "relation": [{"id": str(page_id)} for page_id in value]
            }
    if "person" in data:
        value = data["person"]
        # Convert based on property type
        # Generic handling for other types
        properties["Person"] = {"people": value}
    if "contributors" in data:
        value = data["contributors"]
        # Convert based on property type
        # Generic handling for other types
        properties["Contributors"] = {"people": value}
    if "team" in data:
        value = data["team"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Team"] = {"relation": [{"id": str(page_id)} for page_id in value]}
    if "pinned" in data:
        value = data["pinned"]
        # Convert based on property type
        if isinstance(value, bool):
            properties["Pinned"] = {"checkbox": value}
    if "owned_by" in data:
        value = data["owned_by"]
        # Convert based on property type
        # Generic handling for other types
        properties["Owned By"] = {"people": value}
    if "sub_item" in data:
        value = data["sub_item"]
        # Convert based on property type
        if isinstance(value, list):
            properties["Sub-item"] = {
                "relation": [{"id": str(page_id)} for page_id in value]
            }
    if "name" in data:
        value = data["name"]
        # Convert based on property type
        if isinstance(value, str):
            properties["Name"] = {"title": [{"text": {"content": value}}]}
    if "in_charge" in data:
        value = data["in_charge"]
        # Convert based on property type
        # Generic handling for other types
        properties["In Charge"] = {"people": value}
    if "status" in data:
        value = data["status"]
        # Convert based on property type
        # Generic handling for other types
        properties["Status"] = {"status": value}

    # Update the page
    await client.update_page(str(page_id), properties=properties)

    return page_id


async def delete_documents(client: NotionClient, page_id: DocumentsID) -> DocumentsID:
    """Delete (archive) a Documents entry.

    Args:
        client: Notion client instance
        page_id: ID of the page to delete

    Returns:
        ID of the deleted page
    """
    await client.update_page(str(page_id), archived=True)
    return page_id


async def list_documentss(
    client: NotionClient, limit: int = 100, filter_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """List Documents entries.

    Args:
        client: Notion client instance
        limit: Maximum number of entries to return
        filter_data: Optional filter criteria

    Returns:
        List of dictionaries containing the page properties
    """
    # Build query
    query_data = {"page_size": limit}

    if filter_data:
        query_data["filter"] = filter_data

    # Query the database
    response = await client.query_database(
        "55909df8-1f56-40c4-9327-bab99b4f97f5", **query_data
    )

    # Extract data from each page
    results = []
    for page in response.get("results", []):
        page_data = {"id": DocumentsID(page["id"])}
        properties = page.get("properties", {})

        # Extract Events/Projects
        if "Events/Projects" in properties:
            prop_data = properties["Events/Projects"]
            if prop_data.get("relation"):
                page_data["events_projects"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Parent item
        if "Parent item" in properties:
            prop_data = properties["Parent item"]
            if prop_data.get("relation"):
                page_data["parent_item"] = [rel["id"] for rel in prop_data["relation"]]
        # Extract Last edited by
        if "Last edited by" in properties:
            prop_data = properties["Last edited by"]
            page_data["last_edited_by"] = prop_data.get("last_edited_by")
        # Extract Google Drive File
        if "Google Drive File" in properties:
            prop_data = properties["Google Drive File"]
            if prop_data.get("relation"):
                page_data["google_drive_file"] = [
                    rel["id"] for rel in prop_data["relation"]
                ]
        # Extract Person
        if "Person" in properties:
            prop_data = properties["Person"]
            page_data["person"] = prop_data.get("people")
        # Extract Contributors
        if "Contributors" in properties:
            prop_data = properties["Contributors"]
            page_data["contributors"] = prop_data.get("people")
        # Extract Team
        if "Team" in properties:
            prop_data = properties["Team"]
            if prop_data.get("relation"):
                page_data["team"] = [rel["id"] for rel in prop_data["relation"]]
        # Extract Pinned
        if "Pinned" in properties:
            prop_data = properties["Pinned"]
            page_data["pinned"] = prop_data.get("checkbox", False)
        # Extract Owned By
        if "Owned By" in properties:
            prop_data = properties["Owned By"]
            page_data["owned_by"] = prop_data.get("people")
        # Extract Sub-item
        if "Sub-item" in properties:
            prop_data = properties["Sub-item"]
            if prop_data.get("relation"):
                page_data["sub_item"] = [rel["id"] for rel in prop_data["relation"]]
        # Extract Name
        if "Name" in properties:
            prop_data = properties["Name"]
            if prop_data.get("title"):
                page_data["name"] = "".join(
                    text.get("plain_text", "") for text in prop_data["title"]
                )
        # Extract In Charge
        if "In Charge" in properties:
            prop_data = properties["In Charge"]
            page_data["in_charge"] = prop_data.get("people")
        # Extract Status
        if "Status" in properties:
            prop_data = properties["Status"]
            page_data["status"] = prop_data.get("status")

        results.append(page_data)

    return results


# Test Functions


async def test_documents_crud():
    """Test CRUD operations for Documents."""
    import os
    from notion_framework.client.client import NotionClient

    # Initialize client
    token = os.getenv("NOTION_TOKEN")
    if not token:
        print("❌ NOTION_TOKEN environment variable is required for testing")
        return

    client = NotionClient(token)

    try:
        print("🧪 Testing Documents CRUD operations...")

        # Test data
        test_data = {
            "name": "Test Documents Entry",
        }

        # Test CREATE
        print("  ✅ Testing CREATE...")
        page_id = await create_documents(client, test_data)
        print(f"     Created page: {page_id}")

        # Test READ
        print("  ✅ Testing READ...")
        data = await read_documents(client, page_id)
        print(f"     Read data: {data}")

        # Test UPDATE
        print("  ✅ Testing UPDATE...")
        update_data = {
            "name": "Updated Test Entry",
        }
        await update_documents(client, page_id, update_data)
        print("     Updated page")

        # Test LIST
        print("  ✅ Testing LIST...")
        results = await list_documentss(client, limit=5)
        print(f"     Found {len(results)} entries")

        # Test DELETE
        print("  ✅ Testing DELETE...")
        await delete_documents(client, page_id)
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

    asyncio.run(test_documents_crud())
