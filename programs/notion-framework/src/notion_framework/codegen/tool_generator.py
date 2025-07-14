"""Tool generation for Notion databases."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from ..client.exceptions import CodeGenerationError
from ..types.database import DatabaseSchema, WorkspaceSchema
from .template_engine import TemplateEngine

logger = logging.getLogger(__name__)


class ToolGenerator:
    """Generates LLMgine tools from Notion database schemas."""
    
    def __init__(self, template_engine: TemplateEngine):
        self.template_engine = template_engine
    
    def generate_database_tools(self, schema: DatabaseSchema) -> str:
        """Generate tools for a single database."""
        try:
            logger.info(f"Generating tools for database '{schema.title}'")
            
            # Prepare context for template
            context = self._prepare_database_context(schema)
            
            # Render the template
            code = self.template_engine.render_template("tools.py.j2", context)
            
            logger.info(f"Successfully generated tools for database '{schema.title}'")
            return code
            
        except Exception as e:
            logger.error(f"Failed to generate tools for database '{schema.title}': {e}")
            raise CodeGenerationError(f"Tool generation failed: {e}")
    
    def generate_database_tools_file(self, schema: DatabaseSchema, output_dir: Path) -> Path:
        """Generate and write database tools to file."""
        try:
            # Generate the code
            code = self.generate_database_tools(schema)
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            filename = self._get_tools_filename(schema)
            file_path = output_dir / filename
            
            # Write the file
            file_path.write_text(code, encoding="utf-8")
            
            logger.info(f"Generated tools file: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to generate tools file for '{schema.title}': {e}")
            raise CodeGenerationError(f"Tools file generation failed: {e}")
    
    def generate_workspace_tools(self, workspace: WorkspaceSchema, output_dir: Path) -> List[Path]:
        """Generate tools for all databases in a workspace."""
        generated_files = []
        
        logger.info(f"Generating tools for workspace with {workspace.database_count} databases")
        
        # Create main tools directory
        tools_dir = output_dir / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate tools for each database
        for database_id, schema in workspace.databases.items():
            try:
                file_path = self.generate_database_tools_file(schema, tools_dir)
                generated_files.append(file_path)
            except Exception as e:
                logger.warning(f"Skipped tools generation for database '{schema.title}': {e}")
                continue
        
        # Generate workspace-level tool registry
        registry_file = self.generate_tool_registry(workspace, tools_dir)
        generated_files.append(registry_file)
        
        # Generate __init__.py
        init_file = self.generate_tools_init(workspace, tools_dir)
        generated_files.append(init_file)
        
        logger.info(f"Generated {len(generated_files)} tool files")
        return generated_files
    
    def generate_tool_registry(self, workspace: WorkspaceSchema, output_dir: Path) -> Path:
        """Generate a registry of all tools in the workspace."""
        try:
            logger.info("Generating tool registry")
            
            # Prepare context
            context = {
                "workspace": {
                    "databases": []
                }
            }
            
            for database_id, schema in workspace.databases.items():
                database_info = {
                    "id": schema.id,
                    "title": schema.title,
                    "class_name": self._normalize_class_name(schema.title),
                    "module_name": self._normalize_filename(schema.title),
                    "tools_module": f"{self._normalize_filename(schema.title)}_tools",
                }
                context["workspace"]["databases"].append(database_info)
            
            # Generate registry code
            registry_template = '''"""Tool registry for all generated Notion tools."""

from typing import List
from llmgine.llm.tools import Tool

{% for db in workspace.databases %}
from .{{ db.tools_module }} import TOOLS as {{ db.class_name | upper }}_TOOLS
{% endfor %}

# All generated tools
ALL_TOOLS: List[Tool] = []

{% for db in workspace.databases %}
ALL_TOOLS.extend({{ db.class_name | upper }}_TOOLS)
{% endfor %}

# Tools by database
TOOLS_BY_DATABASE = {
{% for db in workspace.databases %}
    "{{ db.id }}": {{ db.class_name | upper }}_TOOLS,
{% endfor %}
}

def get_all_tools() -> List[Tool]:
    """Get all generated tools."""
    return ALL_TOOLS

def get_tools_for_database(database_id: str) -> List[Tool]:
    """Get tools for a specific database."""
    return TOOLS_BY_DATABASE.get(database_id, [])

def get_database_ids() -> List[str]:
    """Get all database IDs."""
    return list(TOOLS_BY_DATABASE.keys())
'''
            
            code = self.template_engine.render_template_string(registry_template, context)
            
            # Write to file
            file_path = output_dir / "registry.py"
            file_path.write_text(code, encoding="utf-8")
            
            logger.info(f"Generated tool registry: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to generate tool registry: {e}")
            raise CodeGenerationError(f"Tool registry generation failed: {e}")
    
    def generate_tools_init(self, workspace: WorkspaceSchema, output_dir: Path) -> Path:
        """Generate __init__.py for tools package."""
        try:
            # Prepare context
            context = {
                "workspace": {
                    "databases": []
                }
            }
            
            for database_id, schema in workspace.databases.items():
                database_info = {
                    "class_name": self._normalize_class_name(schema.title),
                    "tools_module": f"{self._normalize_filename(schema.title)}_tools",
                }
                context["workspace"]["databases"].append(database_info)
            
            # Generate init code
            init_template = '''"""Generated Notion tools package."""

from .registry import get_all_tools, get_tools_for_database, get_database_ids

{% for db in workspace.databases %}
from .{{ db.tools_module }} import TOOLS as {{ db.class_name | upper }}_TOOLS
{% endfor %}

__all__ = [
    "get_all_tools",
    "get_tools_for_database", 
    "get_database_ids",
{% for db in workspace.databases %}
    "{{ db.class_name | upper }}_TOOLS",
{% endfor %}
]
'''
            
            code = self.template_engine.render_template_string(init_template, context)
            
            # Write to file
            file_path = output_dir / "__init__.py"
            file_path.write_text(code, encoding="utf-8")
            
            logger.info(f"Generated tools __init__.py: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to generate tools __init__.py: {e}")
            raise CodeGenerationError(f"Tools __init__.py generation failed: {e}")
    
    def _prepare_database_context(self, schema: DatabaseSchema) -> Dict[str, Any]:
        """Prepare template context for database tools."""
        # Convert property definitions to template-friendly format
        properties = {}
        for prop_name, prop_def in schema.properties.items():
            properties[prop_name] = {
                "name": prop_def.name,
                "type": prop_def.type,
                "id": prop_def.id,
                "is_editable": prop_def.is_editable,
                "is_required": prop_def.is_required,
                "config": prop_def.config,
            }
            
            # Add type-specific data
            if prop_def.type == "select" and prop_def.select_options:
                properties[prop_name]["select_options"] = prop_def.select_options
            elif prop_def.type == "multi_select" and prop_def.multi_select_options:
                properties[prop_name]["multi_select_options"] = prop_def.multi_select_options
            elif prop_def.type == "relation" and prop_def.relation_database_id:
                properties[prop_name]["relation_database_id"] = prop_def.relation_database_id
            elif prop_def.type == "rollup" and prop_def.rollup_config:
                properties[prop_name]["rollup_config"] = prop_def.rollup_config
            elif prop_def.type == "formula" and prop_def.formula_expression:
                properties[prop_name]["formula_expression"] = prop_def.formula_expression
        
        return {
            "database": {
                "id": schema.id,
                "title": schema.title,
                "description": schema.description,
                "url": schema.url,
                "properties": properties,
                "created_time": schema.created_time,
                "last_edited_time": schema.last_edited_time,
                "archived": schema.archived,
                "is_inline": schema.is_inline,
            }
        }
    
    def _get_tools_filename(self, schema: DatabaseSchema) -> str:
        """Generate filename for database tools."""
        normalized = self._normalize_filename(schema.title)
        return f"{normalized}_tools.py"
    
    def _normalize_filename(self, name: str) -> str:
        """Normalize name for filename."""
        import re
        # Replace spaces and special characters with underscores
        normalized = name.lower().replace(" ", "_").replace("-", "_")
        normalized = re.sub(r'[^a-zA-Z0-9_]', '_', normalized)
        
        # Ensure it's a valid Python module name
        if normalized and normalized[0].isdigit():
            normalized = f"db_{normalized}"
        
        # Remove consecutive underscores
        normalized = re.sub(r'_+', '_', normalized)
        normalized = normalized.strip('_')
        
        return normalized or "unnamed_database"
    
    def _normalize_class_name(self, name: str) -> str:
        """Normalize name for class name."""
        import re
        # Split on spaces and special characters, capitalize each part
        parts = re.split(r'[^a-zA-Z0-9]', name)
        parts = [part.capitalize() for part in parts if part]
        
        class_name = "".join(parts)
        
        # Ensure it starts with a letter
        if class_name and class_name[0].isdigit():
            class_name = f"Database{class_name}"
        
        return class_name or "UnnamedDatabase"
    
    def generate_custom_tools(
        self,
        schema: DatabaseSchema,
        tool_definitions: List[Dict[str, Any]]
    ) -> str:
        """Generate custom tools based on provided definitions."""
        try:
            logger.info(f"Generating {len(tool_definitions)} custom tools for '{schema.title}'")
            
            # Prepare context
            context = self._prepare_database_context(schema)
            context["custom_tools"] = tool_definitions
            
            # Custom template for additional tools
            custom_template = '''"""Custom tools for {{ database.title }}."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from llmgine.llm.tools import Tool, Parameter
from notion_framework.client.client import NotionClient

from .{{ database.title | normalize_class_name | snake_case }} import {{ database.title | normalize_class_name }}

{% for tool in custom_tools %}

async def {{ tool.function_name }}(
    client: NotionClient,
{% for param in tool.parameters %}
    {{ param.name }}: {{ param.type }}{% if not param.required %} = None{% endif %},
{% endfor %}
) -> str:
    """{{ tool.description }}"""
    # Custom implementation
    {{ tool.implementation | indent(4) }}

{% endfor %}

# Custom tool definitions
CUSTOM_TOOLS = [
{% for tool in custom_tools %}
    Tool(
        name="{{ tool.name }}",
        description="{{ tool.description }}",
        parameters=[
{% for param in tool.parameters %}
            Parameter(
                name="{{ param.name }}",
                description="{{ param.description }}",
                type="{{ param.type }}",
                required={{ param.required }}
            ),
{% endfor %}
        ],
        function={{ tool.function_name }},
        is_async=True
    ),
{% endfor %}
]
'''
            
            code = self.template_engine.render_template_string(custom_template, context)
            return code
            
        except Exception as e:
            logger.error(f"Failed to generate custom tools: {e}")
            raise CodeGenerationError(f"Custom tool generation failed: {e}")
    
    def get_suggested_tools(self, schema: DatabaseSchema) -> List[Dict[str, Any]]:
        """Get suggested tool implementations for a database."""
        suggestions = []
        
        # Analyze schema for common patterns
        has_status = any(p.type in ["select", "status"] for p in schema.properties.values())
        has_assignee = any("assign" in p.name.lower() or "owner" in p.name.lower()
                          for p in schema.properties.values() if p.type == "people")
        has_priority = any("priority" in p.name.lower()
                          for p in schema.properties.values() if p.type == "select")
        has_due_date = any("due" in p.name.lower() or "deadline" in p.name.lower()
                          for p in schema.properties.values() if p.type == "date")
        
        # Task/Project management patterns
        if has_status and has_assignee:
            suggestions.append({
                "name": f"assign_{self._normalize_filename(schema.title)}",
                "description": f"Assign a {schema.title} to someone",
                "function_name": f"assign_{self._normalize_filename(schema.title)}",
                "parameters": [
                    {"name": "page_id", "type": "str", "required": True, "description": "Page ID"},
                    {"name": "user_id", "type": "str", "required": True, "description": "User to assign to"}
                ],
                "implementation": "# Assign logic here\npass"
            })
        
        if has_due_date:
            suggestions.append({
                "name": f"set_{self._normalize_filename(schema.title)}_due_date",
                "description": f"Set due date for a {schema.title}",
                "function_name": f"set_{self._normalize_filename(schema.title)}_due_date",
                "parameters": [
                    {"name": "page_id", "type": "str", "required": True, "description": "Page ID"},
                    {"name": "due_date", "type": "str", "required": True, "description": "Due date"}
                ],
                "implementation": "# Set due date logic here\npass"
            })
        
        if has_priority:
            suggestions.append({
                "name": f"prioritize_{self._normalize_filename(schema.title)}",
                "description": f"Set priority for a {schema.title}",
                "function_name": f"prioritize_{self._normalize_filename(schema.title)}",
                "parameters": [
                    {"name": "page_id", "type": "str", "required": True, "description": "Page ID"},
                    {"name": "priority", "type": "str", "required": True, "description": "Priority level"}
                ],
                "implementation": "# Set priority logic here\npass"
            })
        
        return suggestions
