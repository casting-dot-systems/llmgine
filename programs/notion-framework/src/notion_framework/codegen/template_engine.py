"""Jinja2 template engine for code generation."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader

from ..client.exceptions import CodeGenerationError

logger = logging.getLogger(__name__)


class TemplateEngine:
    """Manages Jinja2 templates for code generation."""
    
    def __init__(self, template_dir: Optional[Path] = None):
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"
        
        self.template_dir = Path(template_dir)
        
        # Configure Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        
        # Add custom filters
        self.env.filters.update({
            'normalize_name': self._normalize_name,
            'normalize_class_name': self._normalize_class_name,
            'normalize_enum_value': self._normalize_enum_value,
            'python_type': self._get_python_type,
            'json_schema_type': self._get_json_schema_type,
            'notion_type': self._get_notion_type,
            'is_editable': lambda prop: prop.get('is_editable', True),
            'is_required': lambda prop: prop.get('is_required', False),
            'snake_case': self._to_snake_case,
            'camel_case': self._to_camel_case,
            'pascal_case': self._to_pascal_case,
        })
        
        # Add custom functions
        self.env.globals.update({
            'get_imports': self._get_imports,
            'get_property_options': self._get_property_options,
        })
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with the given context."""
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise CodeGenerationError(f"Template rendering failed: {e}", template_name)
    
    def render_template_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render a template string with the given context."""
        try:
            template = self.env.from_string(template_string)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template string: {e}")
            raise CodeGenerationError(f"Template string rendering failed: {e}")
    
    def list_templates(self) -> list[str]:
        """List all available templates."""
        try:
            return self.env.list_templates()
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []
    
    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists."""
        try:
            self.env.get_template(template_name)
            return True
        except Exception:
            return False
    
    # Custom filters
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for Python variable names."""
        import re
        # Replace spaces and special characters with underscores
        normalized = name.lower().replace(" ", "_").replace("-", "_")
        normalized = re.sub(r'[^a-zA-Z0-9_]', '_', normalized)
        
        # Ensure it starts with a letter or underscore
        if normalized and normalized[0].isdigit():
            normalized = f"_{normalized}"
        
        # Handle Python keywords
        python_keywords = {
            "False", "None", "True", "and", "as", "assert", "break", "class",
            "continue", "def", "del", "elif", "else", "except", "finally",
            "for", "from", "global", "if", "import", "in", "is", "lambda",
            "nonlocal", "not", "or", "pass", "raise", "return", "try",
            "while", "with", "yield"
        }
        
        if normalized.lower() in {kw.lower() for kw in python_keywords}:
            normalized += "_prop"
        
        return normalized or "unnamed"
    
    def _normalize_class_name(self, name: str) -> str:
        """Normalize name for Python class names."""
        import re
        # Split on spaces and special characters, capitalize each part
        parts = re.split(r'[^a-zA-Z0-9]', name)
        parts = [part.capitalize() for part in parts if part]
        
        class_name = "".join(parts)
        
        # Ensure it starts with a letter
        if class_name and class_name[0].isdigit():
            class_name = f"Database{class_name}"
        
        return class_name or "UnnamedDatabase"
    
    def _normalize_enum_value(self, name: str) -> str:
        """Normalize a name to a valid Python enum value."""
        import re
        # Convert to uppercase and replace invalid characters
        normalized = name.upper().replace(' ', '_').replace('-', '_')
        normalized = re.sub(r'[^A-Z0-9_]', '_', normalized)
        # Ensure it starts with a letter
        if normalized and normalized[0].isdigit():
            normalized = f'_{normalized}'
        return normalized or 'UNNAMED'
    
    def _to_snake_case(self, name: str) -> str:
        """Convert to snake_case."""
        import re
        # Insert underscores before capital letters (except at start)
        s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
        # Insert underscores before capital letters preceded by lowercase
        s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower()
    
    def _to_camel_case(self, name: str) -> str:
        """Convert to camelCase."""
        components = name.replace('_', ' ').replace('-', ' ').split()
        if not components:
            return name
        
        return components[0].lower() + ''.join(word.capitalize() for word in components[1:])
    
    def _to_pascal_case(self, name: str) -> str:
        """Convert to PascalCase."""
        components = name.replace('_', ' ').replace('-', ' ').split()
        return ''.join(word.capitalize() for word in components)
    
    def _get_python_type(self, prop_type: str, options: Optional[list] = None) -> str:
        """Get Python type annotation for a property type."""
        type_map = {
            "title": "str",
            "rich_text": "str",
            "number": "Union[int, float, None]",
            "select": "Optional[str]",
            "multi_select": "List[str]",
            "date": "Optional[datetime]",
            "people": "List[str]",
            "files": "List[str]",
            "checkbox": "bool",
            "url": "Optional[str]",
            "email": "Optional[str]",
            "phone_number": "Optional[str]",
            "formula": "Any",
            "relation": "List[str]",
            "rollup": "Any",
            "created_time": "datetime",
            "created_by": "str",
            "last_edited_time": "datetime",
            "last_edited_by": "str",
            "status": "Optional[str]",
            "unique_id": "str",
        }
        
        base_type = type_map.get(prop_type, "Any")
        
        # Handle select with options
        if prop_type == "select" and options and len(options) <= 10:
            option_literals = [f'"{opt["name"]}"' for opt in options]
            return f'Optional[Literal[{", ".join(option_literals)}]]'
        
        return base_type
    
    def _get_json_schema_type(self, prop_type: str) -> str:
        """Get JSON schema type for Tool parameters."""
        from ..schema.mapper import TypeMapper
        
        # Create a minimal PropertyDefinition-like object
        class MockProp:
            def __init__(self, type_name):
                self.type = type_name
        
        mapper = TypeMapper()
        return mapper.get_json_schema_type(MockProp(prop_type))
    
    def _get_notion_type(self, prop_type: str) -> str:
        """Get Notion property class name for a property type."""
        class_map = {
            "title": "NotionTitle",
            "rich_text": "NotionText",
            "number": "NotionNumber",
            "select": "NotionSelect",
            "multi_select": "NotionMultiSelect",
            "date": "NotionDate",
            "people": "NotionPeople",
            "files": "NotionFiles",
            "checkbox": "NotionCheckbox",
            "url": "NotionURL",
            "email": "NotionEmail",
            "phone_number": "NotionPhoneNumber",
            "formula": "NotionFormula",
            "relation": "NotionRelation",
            "rollup": "NotionRollup",
            "created_time": "NotionCreatedTime",
            "created_by": "NotionCreatedBy",
            "last_edited_time": "NotionLastEditedTime",
            "last_edited_by": "NotionLastEditedBy",
            "status": "NotionStatus",
            "unique_id": "NotionUniqueID",
        }
        
        return class_map.get(prop_type, "NotionProperty")
    
    # Custom global functions
    
    def _get_imports(self, properties: Dict[str, Any]) -> list[str]:
        """Generate import statements for properties."""
        imports = set()
        
        # Always import base types
        imports.add("from typing import Any, Dict, List, Optional, Union")
        imports.add("from datetime import datetime")
        imports.add("from pydantic import BaseModel, Field")
        
        # Check if we need Literal
        needs_literal = any(
            prop.get("type") in ["select", "multi_select"] and prop.get("options")
            for prop in properties.values()
        )
        if needs_literal:
            imports.add("from typing import Literal")
        
        # Import Notion property classes
        used_classes = set()
        for prop in properties.values():
            notion_class = self._get_notion_type(prop.get("type", ""))
            if notion_class != "NotionProperty":
                used_classes.add(notion_class)
        
        if used_classes:
            notion_imports = ", ".join(sorted(used_classes))
            imports.add(f"from notion_framework.types.properties import {notion_imports}")
        
        return sorted(list(imports))
    
    def _get_property_options(self, prop: Dict[str, Any]) -> Optional[list]:
        """Get options for select/multi-select properties."""
        prop_type = prop.get("type", "")
        if prop_type == "select":
            return prop.get("select_options", [])
        elif prop_type == "multi_select":
            return prop.get("multi_select_options", [])
        return None
