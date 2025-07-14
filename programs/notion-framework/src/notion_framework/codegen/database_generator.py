"""Database class code generator."""

import logging
from pathlib import Path
from typing import Any, Dict

from ..client.exceptions import CodeGenerationError
from ..types.database import DatabaseSchema
from .template_engine import TemplateEngine

logger = logging.getLogger(__name__)


class DatabaseGenerator:
    """Generates typed database classes from Notion schemas."""
    
    def __init__(self, template_engine: TemplateEngine):
        self.template_engine = template_engine
    
    def generate_database_class(self, schema: DatabaseSchema) -> str:
        """Generate a typed database class from schema."""
        try:
            logger.info(f"Generating database class for '{schema.title}'")
            
            # Prepare context for template
            context = self._prepare_context(schema)
            
            # Render the template
            code = self.template_engine.render_template("database.py.j2", context)
            
            logger.info(f"Successfully generated database class for '{schema.title}'")
            return code
            
        except Exception as e:
            logger.error(f"Failed to generate database class for '{schema.title}': {e}")
            raise CodeGenerationError(f"Database class generation failed: {e}")
    
    def generate_database_file(self, schema: DatabaseSchema, output_dir: Path) -> Path:
        """Generate and write database class to file."""
        try:
            # Generate the code
            code = self.generate_database_class(schema)
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            filename = self._get_filename(schema)
            file_path = output_dir / filename
            
            # Write the file
            file_path.write_text(code, encoding="utf-8")
            
            logger.info(f"Generated database file: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to generate database file for '{schema.title}': {e}")
            raise CodeGenerationError(f"Database file generation failed: {e}")
    
    def _prepare_context(self, schema: DatabaseSchema) -> Dict[str, Any]:
        """Prepare template context from database schema."""
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
    
    def _get_filename(self, schema: DatabaseSchema) -> str:
        """Generate filename for database class."""
        # Normalize the database title to a valid Python module name
        normalized = self._normalize_filename(schema.title)
        return f"{normalized}.py"
    
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
    
    def validate_schema_for_generation(self, schema: DatabaseSchema) -> list[str]:
        """Validate that schema is suitable for code generation."""
        issues = []
        
        # Check basic requirements
        if not schema.title:
            issues.append("Database must have a title")
        
        if not schema.properties:
            issues.append("Database must have properties")
        
        # Check for title property
        title_props = [p for p in schema.properties.values() if p.type == "title"]
        if not title_props:
            issues.append("Database must have a title property")
        
        # Check for problematic property names
        python_keywords = {
            "False", "None", "True", "and", "as", "assert", "break", "class",
            "continue", "def", "del", "elif", "else", "except", "finally",
            "for", "from", "global", "if", "import", "in", "is", "lambda",
            "nonlocal", "not", "or", "pass", "raise", "return", "try",
            "while", "with", "yield"
        }
        
        for prop_name in schema.properties.keys():
            normalized = self._normalize_property_name(prop_name)
            if normalized.lower() in {kw.lower() for kw in python_keywords}:
                issues.append(f"Property '{prop_name}' conflicts with Python keyword")
        
        return issues
    
    def _normalize_property_name(self, name: str) -> str:
        """Normalize property name for Python."""
        import re
        normalized = name.lower().replace(" ", "_").replace("-", "_")
        normalized = re.sub(r'[^a-zA-Z0-9_]', '_', normalized)
        
        if normalized and normalized[0].isdigit():
            normalized = f"_{normalized}"
        
        return normalized or "unnamed_property"
