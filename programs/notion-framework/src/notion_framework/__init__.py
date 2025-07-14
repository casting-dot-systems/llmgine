"""
Notion Framework - A tool generation framework for Notion databases.

This framework analyzes Notion database schemas and generates typed tools
that integrate with the LLMgine framework.
"""

__version__ = "0.1.0"

from .client.client import NotionClient
from .client.exceptions import NotionFrameworkError
from .integration.framework import NotionFramework

__all__ = [
    "NotionClient",
    "NotionFramework",
    "NotionFrameworkError",
]
