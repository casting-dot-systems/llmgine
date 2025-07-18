"""
Notion Framework - A code generation framework for Notion databases.

This framework analyzes Notion database schemas and generates typed CRUD functions
for Python applications.
"""

__version__ = "0.1.0"

from .client.client import NotionClient
from .client.exceptions import NotionFrameworkError
from .framework import NotionFramework

__all__ = [
    "NotionClient",
    "NotionFramework",
    "NotionFrameworkError",
]
