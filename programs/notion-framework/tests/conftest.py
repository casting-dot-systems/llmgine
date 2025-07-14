"""Pytest configuration for notion-framework tests."""

import asyncio
import os
from unittest.mock import Mock
from typing import Dict, Any

import pytest
from llmgine.bus.bus import MessageBus

from notion_framework.client.client import NotionClient, NotionClientConfig
from notion_framework.types.database import DatabaseSchema, PropertyDefinition


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_notion_client():
    """Mock Notion client for testing."""
    client = Mock(spec=NotionClient)
    client.get_database = Mock()
    client.query_database = Mock()
    client.create_page = Mock()
    client.update_page = Mock()
    client.get_page = Mock()
    client.search = Mock()
    client.close = Mock()
    return client


@pytest.fixture
def message_bus():
    """Create a message bus for testing."""
    return MessageBus()


@pytest.fixture
def sample_database_schema():
    """Sample database schema for testing."""
    properties = {
        "Title": PropertyDefinition(
            id="title",
            name="Title", 
            type="title",
            config={"title": {}}
        ),
        "Status": PropertyDefinition(
            id="status",
            name="Status",
            type="select",
            config={"select": {"options": [
                {"id": "1", "name": "Todo", "color": "red"},
                {"id": "2", "name": "In Progress", "color": "yellow"},
                {"id": "3", "name": "Done", "color": "green"}
            ]}},
            select_options=[
                {"id": "1", "name": "Todo", "color": "red"},
                {"id": "2", "name": "In Progress", "color": "yellow"},
                {"id": "3", "name": "Done", "color": "green"}
            ]
        ),
        "Priority": PropertyDefinition(
            id="priority",
            name="Priority",
            type="select",
            config={"select": {"options": [
                {"id": "1", "name": "Low", "color": "gray"},
                {"id": "2", "name": "Medium", "color": "yellow"},
                {"id": "3", "name": "High", "color": "red"}
            ]}},
            select_options=[
                {"id": "1", "name": "Low", "color": "gray"},
                {"id": "2", "name": "Medium", "color": "yellow"},
                {"id": "3", "name": "High", "color": "red"}
            ]
        ),
        "Due Date": PropertyDefinition(
            id="due_date",
            name="Due Date",
            type="date",
            config={"date": {}}
        ),
        "Assignee": PropertyDefinition(
            id="assignee",
            name="Assignee",
            type="people",
            config={"people": {}}
        ),
        "Description": PropertyDefinition(
            id="description",
            name="Description",
            type="rich_text",
            config={"rich_text": {}}
        ),
        "Completed": PropertyDefinition(
            id="completed",
            name="Completed",
            type="checkbox",
            config={"checkbox": {}}
        ),
        "Created": PropertyDefinition(
            id="created",
            name="Created",
            type="created_time",
            config={"created_time": {}}
        )
    }
    
    return DatabaseSchema(
        id="test-database-id",
        title="Test Tasks",
        description="A test database for tasks",
        url="https://notion.so/test-database-id",
        properties=properties
    )


@pytest.fixture
def sample_notion_response():
    """Sample Notion API response for testing."""
    return {
        "object": "database",
        "id": "test-database-id",
        "title": [
            {
                "type": "text",
                "text": {"content": "Test Tasks"},
                "plain_text": "Test Tasks"
            }
        ],
        "description": [
            {
                "type": "text", 
                "text": {"content": "A test database"},
                "plain_text": "A test database"
            }
        ],
        "properties": {
            "Title": {
                "id": "title",
                "type": "title",
                "title": {}
            },
            "Status": {
                "id": "status",
                "type": "select", 
                "select": {
                    "options": [
                        {"id": "1", "name": "Todo", "color": "red"},
                        {"id": "2", "name": "In Progress", "color": "yellow"},
                        {"id": "3", "name": "Done", "color": "green"}
                    ]
                }
            },
            "Due Date": {
                "id": "due_date",
                "type": "date",
                "date": {}
            }
        },
        "parent": {"type": "workspace"},
        "url": "https://notion.so/test-database-id",
        "created_time": "2023-01-01T00:00:00.000Z",
        "last_edited_time": "2023-01-01T00:00:00.000Z",
        "archived": False,
        "is_inline": False
    }


@pytest.fixture
def notion_token():
    """Get Notion token for integration tests."""
    token = os.getenv("NOTION_TOKEN_TEST")
    if not token:
        pytest.skip("NOTION_TOKEN_TEST environment variable not set")
    return token


@pytest.fixture
async def real_notion_client(notion_token):
    """Real Notion client for integration tests."""
    config = NotionClientConfig(auth=notion_token)
    client = NotionClient(config)
    yield client
    await client.close()


# Test markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires NOTION_TOKEN_TEST)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )