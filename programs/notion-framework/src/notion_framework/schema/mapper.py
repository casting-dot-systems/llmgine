"""Type mapping between Notion properties and Python types."""

import logging
from typing import List, Optional, Type

from ..types.database import DatabaseSchema, PropertyDefinition
from ..types.properties import (
    NotionCheckbox,
    NotionCreatedBy,
    NotionCreatedTime,
    NotionDate,
    NotionEmail,
    NotionFiles,
    NotionFormula,
    NotionLastEditedBy,
    NotionLastEditedTime,
    NotionMultiSelect,
    NotionNumber,
    NotionPeople,
    NotionPhoneNumber,
    NotionProperty,
    NotionRelation,
    NotionRollup,
    NotionSelect,
    NotionStatus,
    NotionText,
    NotionTitle,
    NotionUniqueID,
    NotionURL,
)

logger = logging.getLogger(__name__)


class TypeMapper:
    """Maps Notion property types to Python types and generates type annotations."""
    
    # Mapping from Notion property types to Python classes
    PROPERTY_TYPE_MAP = {
        "title": NotionTitle,
        "rich_text": NotionText,
        "number": NotionNumber,
        "select": NotionSelect,
        "multi_select": NotionMultiSelect,
        "date": NotionDate,
        "people": NotionPeople,
        "files": NotionFiles,
        "checkbox": NotionCheckbox,
        "url": NotionURL,
        "email": NotionEmail,
        "phone_number": NotionPhoneNumber,
        "formula": NotionFormula,
        "relation": NotionRelation,
        "rollup": NotionRollup,
        "created_time": NotionCreatedTime,
        "created_by": NotionCreatedBy,
        "last_edited_time": NotionLastEditedTime,
        "last_edited_by": NotionLastEditedBy,
        "status": NotionStatus,
        "unique_id": NotionUniqueID,
    }
    
    # Python type annotations for properties
    PYTHON_TYPE_MAP = {
        "title": "str",
        "rich_text": "str",
        "number": "Union[int, float, None]",
        "select": "Optional[str]",
        "multi_select": "List[str]",
        "date": "Optional[datetime]",
        "people": "List[str]",  # User IDs
        "files": "List[str]",   # File URLs/names
        "checkbox": "bool",
        "url": "Optional[str]",
        "email": "Optional[str]",
        "phone_number": "Optional[str]",
        "formula": "Any",  # Formula result type varies
        "relation": "List[str]",  # Page IDs
        "rollup": "Any",   # Rollup result type varies
        "created_time": "datetime",
        "created_by": "str",  # User ID
        "last_edited_time": "datetime",
        "last_edited_by": "str",  # User ID
        "status": "Optional[str]",
        "unique_id": "str",
    }
    
    def get_python_class(self, property_type: str) -> Optional[Type[NotionProperty]]:
        """Get the Python class for a Notion property type."""
        return self.PROPERTY_TYPE_MAP.get(property_type)
    
    def get_python_type_annotation(self, prop_def: PropertyDefinition) -> str:
        """Get Python type annotation for a property."""
        base_type = self.PYTHON_TYPE_MAP.get(prop_def.type, "Any")
        
        # Handle specific cases
        if prop_def.type == "select" and prop_def.select_options:
            # Create Literal type for select options
            options = [f'"{opt["name"]}"' for opt in prop_def.select_options]
            if len(options) <= 10:  # Only for reasonable number of options
                return f'Optional[Literal[{", ".join(options)}]]'
        
        elif prop_def.type == "multi_select" and prop_def.multi_select_options:
            # For multi-select, we could specify the allowed values in a comment
            options = [opt["name"] for opt in prop_def.multi_select_options]
            if len(options) <= 10:
                return f'List[str]  # Options: {", ".join(options)}'
        
        elif prop_def.type == "relation" and prop_def.relation_database_id:
            # We could reference the related type if known
            return f'List[str]  # References: {prop_def.relation_database_id}'
        
        return base_type
    
    def get_json_schema_type(self, prop_def: PropertyDefinition) -> str:
        """Get JSON schema type for Tool parameters (simpler than Python types)."""
        # Map to basic JSON schema types
        type_map = {
            "title": "string",
            "rich_text": "string",
            "number": "number",
            "select": "string",
            "multi_select": "array",
            "date": "string",
            "people": "array",
            "files": "array",
            "checkbox": "boolean",
            "url": "string",
            "email": "string",
            "phone_number": "string",
            "formula": "string",
            "relation": "array",
            "rollup": "string",
            "created_time": "string",
            "created_by": "string",
            "last_edited_time": "string",
            "last_edited_by": "string",
            "status": "string",
            "unique_id": "string",
        }
        
        return type_map.get(prop_def.type, "string")
    
    def get_notion_class_annotation(self, prop_def: PropertyDefinition) -> str:
        """Get Notion property class annotation."""
        python_class = self.get_python_class(prop_def.type)
        if not python_class:
            return "NotionProperty"
        
        class_name = python_class.__name__
        
        # Add generic type parameters for typed properties
        if prop_def.type == "select" and prop_def.select_options:
            options = [opt["name"] for opt in prop_def.select_options]
            if len(options) <= 10:
                literal_type = f"Literal[{', '.join([f'\"{opt}\"' for opt in options])}]"
                return f"{class_name}[{literal_type}]"
        
        elif prop_def.type == "relation" and prop_def.relation_database_id:
            # Could reference the target database type
            return f'{class_name}["{prop_def.relation_database_id}"]'
        
        return class_name
    
    def generate_property_imports(self, schema: DatabaseSchema) -> List[str]:
        """Generate import statements for properties used in a schema."""
        imports = set()
        
        # Always import base types
        imports.add("from typing import Any, Dict, List, Optional, Union")
        imports.add("from datetime import datetime")
        
        # Check if we need Literal
        needs_literal = any(
            prop.type in ["select", "multi_select"] and
            (prop.select_options or prop.multi_select_options)
            for prop in schema.properties.values()
        )
        if needs_literal:
            imports.add("from typing import Literal")
        
        # Import Notion property classes
        used_classes = set()
        for prop_def in schema.properties.values():
            python_class = self.get_python_class(prop_def.type)
            if python_class:
                used_classes.add(python_class.__name__)
        
        if used_classes:
            notion_imports = ", ".join(sorted(used_classes))
            imports.add(f"from notion_framework.types.properties import {notion_imports}")
        
        return sorted(list(imports))
    
    def create_property_field_definition(self, prop_name: str, prop_def: PropertyDefinition) -> str:
        """Create a Pydantic field definition for a property."""
        python_type = self.get_python_type_annotation(prop_def)
        notion_type = self.get_notion_class_annotation(prop_def)
        
        field_parts = []
        
        # Field definition
        if prop_def.is_required:
            field_parts.append(f"{self._normalize_name(prop_name)}: {python_type}")
        else:
            field_parts.append(f"{self._normalize_name(prop_name)}: {python_type} = None")
        
        # Add metadata
        metadata_parts = []
        metadata_parts.append(f'description="{prop_def.name}"')
        
        if prop_def.type in ["select", "multi_select"] and hasattr(prop_def, f"{prop_def.type}_options"):
            options = getattr(prop_def, f"{prop_def.type}_options", [])
            if options:
                option_names = [opt["name"] for opt in options]
                metadata_parts.append(f'enum={option_names}')
        
        if metadata_parts:
            field_parts.append(f' = Field({", ".join(metadata_parts)})')
        
        return "    " + "".join(field_parts)
    
    def create_notion_property_field(self, prop_name: str, prop_def: PropertyDefinition) -> str:
        """Create a Notion property field definition."""
        notion_type = self.get_notion_class_annotation(prop_def)
        normalized_name = self._normalize_name(prop_name)
        
        if prop_def.is_required:
            return f"    _{normalized_name}_notion: {notion_type}"
        else:
            return f"    _{normalized_name}_notion: Optional[{notion_type}] = None"
    
    def map_database_to_python_class_name(self, schema: DatabaseSchema) -> str:
        """Generate a Python class name for a database."""
        # Normalize the database title
        class_name = self._normalize_class_name(schema.title)
        
        # Ensure it doesn't conflict with Python keywords
        if class_name.lower() in {"class", "def", "import", "from", "if", "else", "try", "except"}:
            class_name += "Database"
        
        return class_name
    
    def map_property_to_python_name(self, prop_name: str) -> str:
        """Map a Notion property name to a Python variable name."""
        return self._normalize_name(prop_name)
    
    def generate_property_converter_method(self, prop_name: str, prop_def: PropertyDefinition) -> str:
        """Generate method to convert between Python and Notion property formats."""
        normalized_name = self._normalize_name(prop_name)
        python_class = self.get_python_class(prop_def.type)
        
        if not python_class:
            return ""
        
        method_lines = [
            f"    def set_{normalized_name}(self, value: {self.get_python_type_annotation(prop_def)}) -> None:",
            f'        """Set {prop_name} property."""',
        ]
        
        # Generate conversion logic based on property type
        if prop_def.type in ["title", "rich_text"]:
            method_lines.extend([
                "        if isinstance(value, str):",
                f"            self._{normalized_name}_notion = {python_class.__name__}(value)",
                "        else:",
                f"            self._{normalized_name}_notion = value"
            ])
        elif prop_def.type == "number" or prop_def.type in ["select", "status"] or prop_def.type == "checkbox":
            method_lines.extend([
                f"        self._{normalized_name}_notion = {python_class.__name__}(value)"
            ])
        else:
            # Generic conversion
            method_lines.extend([
                f"        self._{normalized_name}_notion = {python_class.__name__}(value)"
            ])
        
        method_lines.append("")
        
        # Generate getter method
        method_lines.extend([
            f"    def get_{normalized_name}(self) -> {self.get_python_type_annotation(prop_def)}:",
            f'        """Get {prop_name} property value."""',
            f"        if self._{normalized_name}_notion is None:",
            "            return None",
        ])
        
        # Generate getter logic based on property type
        if prop_def.type in ["title", "rich_text"]:
            method_lines.append(f"        return self._{normalized_name}_notion.plain_text")
        elif prop_def.type == "number":
            method_lines.append(f"        return self._{normalized_name}_notion.number")
        elif prop_def.type in ["select", "status"]:
            method_lines.append(f"        return self._{normalized_name}_notion.value")
        elif prop_def.type == "multi_select":
            method_lines.append(f"        return self._{normalized_name}_notion.values")
        elif prop_def.type == "checkbox":
            method_lines.append(f"        return self._{normalized_name}_notion.checkbox")
        elif prop_def.type == "date":
            method_lines.append(f"        return self._{normalized_name}_notion.start_date")
        elif prop_def.type == "people":
            method_lines.append(f"        return self._{normalized_name}_notion.user_ids")
        elif prop_def.type == "relation":
            method_lines.append(f"        return self._{normalized_name}_notion.page_ids")
        else:
            method_lines.append(f"        return self._{normalized_name}_notion")
        
        method_lines.append("")
        
        return "\n".join(method_lines)
    
    def _normalize_name(self, name: str) -> str:
        """Normalize a name for Python variable names."""
        # Replace spaces and special characters with underscores
        normalized = name.lower().replace(" ", "_").replace("-", "_")
        
        # Remove other problematic characters
        import re
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
        
        if normalized in {kw.lower() for kw in python_keywords}:
            normalized += "_prop"
        
        return normalized or "unnamed_property"
    
    def _normalize_class_name(self, name: str) -> str:
        """Normalize a name for Python class names."""
        # Split on spaces and special characters, capitalize each part
        import re
        parts = re.split(r'[^a-zA-Z0-9]', name)
        parts = [part.capitalize() for part in parts if part]
        
        class_name = "".join(parts)
        
        # Ensure it starts with a letter
        if class_name and class_name[0].isdigit():
            class_name = f"Database{class_name}"
        
        return class_name or "UnnamedDatabase"
