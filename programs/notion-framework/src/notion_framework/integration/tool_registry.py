"""Tool registry for managing Notion framework tools."""

import logging
from typing import Any, Dict, List, Optional

from llmgine.llm.tools import Tool

logger = logging.getLogger(__name__)


class NotionToolRegistry:
    """Registry for managing Notion framework tools."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.tools_by_database: Dict[str, List[Tool]] = {}
        self.tool_categories: Dict[str, List[Tool]] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(
        self,
        tool: Tool,
        database_id: Optional[str] = None,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a tool with optional categorization."""
        if tool.name in self.tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        
        self.tools[tool.name] = tool
        
        # Associate with database
        if database_id:
            if database_id not in self.tools_by_database:
                self.tools_by_database[database_id] = []
            self.tools_by_database[database_id].append(tool)
        
        # Categorize tool
        if category:
            if category not in self.tool_categories:
                self.tool_categories[category] = []
            self.tool_categories[category].append(tool)
        else:
            # Auto-categorize based on tool name
            category = self._auto_categorize_tool(tool.name)
            if category not in self.tool_categories:
                self.tool_categories[category] = []
            self.tool_categories[category].append(tool)
        
        # Store metadata
        if metadata:
            self.tool_metadata[tool.name] = metadata
        
        logger.info(f"Registered tool '{tool.name}' in category '{category}'")
    
    def register_tools(
        self,
        tools: List[Tool],
        database_id: Optional[str] = None,
        category: Optional[str] = None
    ) -> None:
        """Register multiple tools at once."""
        for tool in tools:
            self.register_tool(tool, database_id, category)
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self.tools.values())
    
    def get_tools_by_database(self, database_id: str) -> List[Tool]:
        """Get all tools for a specific database."""
        return self.tools_by_database.get(database_id, [])
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a category."""
        return self.tool_categories.get(category, [])
    
    def get_available_categories(self) -> List[str]:
        """Get all available tool categories."""
        return list(self.tool_categories.keys())
    
    def get_database_ids(self) -> List[str]:
        """Get all database IDs that have tools."""
        return list(self.tools_by_database.keys())
    
    def search_tools(self, query: str) -> List[Tool]:
        """Search tools by name or description."""
        query_lower = query.lower()
        results = []
        
        for tool in self.tools.values():
            if (query_lower in tool.name.lower() or
                query_lower in tool.description.lower()):
                results.append(tool)
        
        return results
    
    def filter_tools(
        self,
        database_id: Optional[str] = None,
        category: Optional[str] = None,
        has_async: Optional[bool] = None,
        name_pattern: Optional[str] = None
    ) -> List[Tool]:
        """Filter tools by various criteria."""
        tools = self.get_all_tools()
        
        if database_id:
            tools = [t for t in tools if t in self.get_tools_by_database(database_id)]
        
        if category:
            tools = [t for t in tools if t in self.get_tools_by_category(category)]
        
        if has_async is not None:
            tools = [t for t in tools if t.is_async == has_async]
        
        if name_pattern:
            pattern_lower = name_pattern.lower()
            tools = [t for t in tools if pattern_lower in t.name.lower()]
        
        return tools
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a tool."""
        tool = self.get_tool(name)
        if not tool:
            return None
        
        # Find database and category
        database_id = None
        for db_id, db_tools in self.tools_by_database.items():
            if tool in db_tools:
                database_id = db_id
                break
        
        category = None
        for cat, cat_tools in self.tool_categories.items():
            if tool in cat_tools:
                category = cat
                break
        
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": [param.to_dict() for param in tool.parameters],
            "is_async": tool.is_async,
            "database_id": database_id,
            "category": category,
            "metadata": self.tool_metadata.get(name, {}),
        }
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the registry."""
        return {
            "total_tools": len(self.tools),
            "databases": len(self.tools_by_database),
            "categories": len(self.tool_categories),
            "async_tools": len([t for t in self.tools.values() if t.is_async]),
            "sync_tools": len([t for t in self.tools.values() if not t.is_async]),
            "tools_by_category": {
                cat: len(tools) for cat, tools in self.tool_categories.items()
            },
            "tools_by_database": {
                db_id: len(tools) for db_id, tools in self.tools_by_database.items()
            }
        }
    
    def export_tool_manifest(self) -> Dict[str, Any]:
        """Export a manifest of all tools for documentation."""
        manifest = {
            "version": "1.0",
            "generated_at": None,  # Would be set by caller
            "tools": {},
            "categories": {},
            "databases": {}
        }
        
        # Export tools
        for tool in self.tools.values():
            manifest["tools"][tool.name] = {
                "description": tool.description,
                "parameters": [
                    {
                        "name": param.name,
                        "description": param.description,
                        "type": param.type,
                        "required": param.required
                    }
                    for param in tool.parameters
                ],
                "is_async": tool.is_async
            }
        
        # Export categories
        manifest["categories"] = {
            cat: [tool.name for tool in tools]
            for cat, tools in self.tool_categories.items()
        }
        
        # Export database associations
        manifest["databases"] = {
            db_id: [tool.name for tool in tools]
            for db_id, tools in self.tools_by_database.items()
        }
        
        return manifest
    
    def clear_registry(self) -> None:
        """Clear all registered tools."""
        self.tools.clear()
        self.tools_by_database.clear()
        self.tool_categories.clear()
        self.tool_metadata.clear()
        logger.info("Cleared tool registry")
    
    def remove_tool(self, name: str) -> bool:
        """Remove a tool from the registry."""
        if name not in self.tools:
            return False
        
        tool = self.tools[name]
        
        # Remove from main registry
        del self.tools[name]
        
        # Remove from database associations
        for db_id, tools in self.tools_by_database.items():
            if tool in tools:
                tools.remove(tool)
        
        # Remove from categories
        for category, tools in self.tool_categories.items():
            if tool in tools:
                tools.remove(tool)
        
        # Remove metadata
        if name in self.tool_metadata:
            del self.tool_metadata[name]
        
        logger.info(f"Removed tool '{name}' from registry")
        return True
    
    def _auto_categorize_tool(self, tool_name: str) -> str:
        """Automatically categorize a tool based on its name."""
        name_lower = tool_name.lower()
        
        if name_lower.startswith("create_"):
            return "create"
        elif name_lower.startswith("update_"):
            return "update"
        elif name_lower.startswith("get_"):
            return "read"
        elif name_lower.startswith("list_"):
            return "list"
        elif name_lower.startswith("delete_") or name_lower.startswith("remove_"):
            return "delete"
        elif name_lower.startswith("search_"):
            return "search"
        elif name_lower.startswith("filter_"):
            return "filter"
        elif "assign" in name_lower:
            return "assignment"
        elif "status" in name_lower or "state" in name_lower:
            return "status"
        elif "priority" in name_lower:
            return "priority"
        elif "relation" in name_lower or "link" in name_lower:
            return "relation"
        elif "toggle" in name_lower:
            return "toggle"
        else:
            return "misc"
