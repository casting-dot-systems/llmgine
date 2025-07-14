"""Schema validation and consistency checking."""

import logging
from typing import Any, List

from ..types.database import DatabaseSchema, WorkspaceSchema

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates Notion database schemas for consistency and correctness."""
    
    def validate_database_schema(self, schema: DatabaseSchema) -> List[str]:
        """Validate a single database schema."""
        issues = []
        
        # Basic validation
        if not schema.id:
            issues.append("Database missing ID")
        
        if not schema.title:
            issues.append("Database missing title")
        
        if not schema.properties:
            issues.append("Database has no properties")
            return issues  # Can't continue without properties
        
        # Property validation
        issues.extend(self._validate_properties(schema))
        
        # Title property validation
        issues.extend(self._validate_title_property(schema))
        
        # Relation property validation
        issues.extend(self._validate_relation_properties(schema))
        
        # Formula property validation
        issues.extend(self._validate_formula_properties(schema))
        
        # Rollup property validation
        issues.extend(self._validate_rollup_properties(schema))
        
        return issues
    
    def validate_workspace_schema(self, workspace: WorkspaceSchema) -> List[str]:
        """Validate an entire workspace schema."""
        issues = []
        
        if not workspace.databases:
            issues.append("Workspace has no databases")
            return issues
        
        # Validate each database individually
        for db_id, schema in workspace.databases.items():
            db_issues = self.validate_database_schema(schema)
            for issue in db_issues:
                issues.append(f"Database '{schema.title}' ({db_id}): {issue}")
        
        # Cross-database validation
        issues.extend(self._validate_cross_database_consistency(workspace))
        
        # Relationship validation
        issues.extend(self._validate_relationships(workspace))
        
        # Naming validation
        issues.extend(self._validate_naming_conventions(workspace))
        
        return issues
    
    def _validate_properties(self, schema: DatabaseSchema) -> List[str]:
        """Validate individual properties."""
        issues = []
        
        supported_types = {
            "title", "rich_text", "number", "select", "multi_select",
            "date", "people", "files", "checkbox", "url", "email",
            "phone_number", "formula", "relation", "rollup",
            "created_time", "created_by", "last_edited_time",
            "last_edited_by", "status", "unique_id"
        }
        
        property_names = set()
        
        for prop_name, prop_def in schema.properties.items():
            # Check for duplicate names (case-insensitive)
            lower_name = prop_name.lower()
            if lower_name in property_names:
                issues.append(f"Duplicate property name: '{prop_name}'")
            property_names.add(lower_name)
            
            # Validate property type
            if prop_def.type not in supported_types:
                issues.append(f"Unsupported property type '{prop_def.type}' for property '{prop_name}'")
            
            # Validate property ID
            if not prop_def.id:
                issues.append(f"Property '{prop_name}' missing ID")
            
            # Type-specific validation
            if prop_def.type == "select":
                issues.extend(self._validate_select_property(prop_name, prop_def))
            elif prop_def.type == "multi_select":
                issues.extend(self._validate_multi_select_property(prop_name, prop_def))
            elif prop_def.type == "relation":
                issues.extend(self._validate_relation_property(prop_name, prop_def))
            elif prop_def.type == "formula":
                issues.extend(self._validate_formula_property(prop_name, prop_def))
            elif prop_def.type == "rollup":
                issues.extend(self._validate_rollup_property(prop_name, prop_def))
        
        return issues
    
    def _validate_title_property(self, schema: DatabaseSchema) -> List[str]:
        """Validate title property requirements."""
        issues = []
        
        title_properties = [
            prop for prop in schema.properties.values()
            if prop.type == "title"
        ]
        
        if len(title_properties) == 0:
            issues.append("Database missing required title property")
        elif len(title_properties) > 1:
            issues.append("Database has multiple title properties (only one allowed)")
        
        return issues
    
    def _validate_select_property(self, prop_name: str, prop_def: Any) -> List[str]:
        """Validate select property configuration."""
        issues = []
        
        if not prop_def.select_options:
            issues.append(f"Select property '{prop_name}' has no options defined")
        else:
            option_names = set()
            for option in prop_def.select_options:
                if not isinstance(option, dict):
                    issues.append(f"Select property '{prop_name}' has invalid option format")
                    continue
                
                option_name = option.get("name", "")
                if not option_name:
                    issues.append(f"Select property '{prop_name}' has option with empty name")
                elif option_name in option_names:
                    issues.append(f"Select property '{prop_name}' has duplicate option: '{option_name}'")
                option_names.add(option_name)
        
        return issues
    
    def _validate_multi_select_property(self, prop_name: str, prop_def: Any) -> List[str]:
        """Validate multi-select property configuration."""
        issues = []
        
        if not prop_def.multi_select_options:
            issues.append(f"Multi-select property '{prop_name}' has no options defined")
        else:
            option_names = set()
            for option in prop_def.multi_select_options:
                if not isinstance(option, dict):
                    issues.append(f"Multi-select property '{prop_name}' has invalid option format")
                    continue
                
                option_name = option.get("name", "")
                if not option_name:
                    issues.append(f"Multi-select property '{prop_name}' has option with empty name")
                elif option_name in option_names:
                    issues.append(f"Multi-select property '{prop_name}' has duplicate option: '{option_name}'")
                option_names.add(option_name)
        
        return issues
    
    def _validate_relation_property(self, prop_name: str, prop_def: Any) -> List[str]:
        """Validate relation property configuration."""
        issues = []
        
        if not prop_def.relation_database_id:
            issues.append(f"Relation property '{prop_name}' missing target database ID")
        
        return issues
    
    def _validate_formula_property(self, prop_name: str, prop_def: Any) -> List[str]:
        """Validate formula property configuration."""
        issues = []
        
        if not prop_def.formula_expression:
            issues.append(f"Formula property '{prop_name}' missing expression")
        
        return issues
    
    def _validate_rollup_property(self, prop_name: str, prop_def: Any) -> List[str]:
        """Validate rollup property configuration."""
        issues = []
        
        if not prop_def.rollup_config:
            issues.append(f"Rollup property '{prop_name}' missing configuration")
        else:
            config = prop_def.rollup_config
            if not config.get("relation_property_name"):
                issues.append(f"Rollup property '{prop_name}' missing relation property name")
            if not config.get("rollup_property_name"):
                issues.append(f"Rollup property '{prop_name}' missing rollup property name")
            if not config.get("function"):
                issues.append(f"Rollup property '{prop_name}' missing function")
        
        return issues
    
    def _validate_relation_properties(self, schema: DatabaseSchema) -> List[str]:
        """Validate all relation properties in a database."""
        issues = []
        
        for prop_name, prop_def in schema.relation_properties.items():
            if not prop_def.relation_database_id:
                issues.append(f"Relation property '{prop_name}' missing target database")
        
        return issues
    
    def _validate_formula_properties(self, schema: DatabaseSchema) -> List[str]:
        """Validate all formula properties in a database."""
        issues = []
        
        formula_props = {
            name: prop for name, prop in schema.properties.items()
            if prop.type == "formula"
        }
        
        # Check for circular dependencies
        for prop_name, prop_def in formula_props.items():
            if prop_def.formula_expression:
                # Simple check for self-reference
                if prop_name in prop_def.formula_expression:
                    issues.append(f"Formula property '{prop_name}' references itself")
        
        return issues
    
    def _validate_rollup_properties(self, schema: DatabaseSchema) -> List[str]:
        """Validate all rollup properties in a database."""
        issues = []
        
        rollup_props = {
            name: prop for name, prop in schema.properties.items()
            if prop.type == "rollup"
        }
        
        for prop_name, prop_def in rollup_props.items():
            if prop_def.rollup_config:
                relation_prop_name = prop_def.rollup_config.get("relation_property_name")
                if relation_prop_name:
                    relation_prop = schema.get_property_by_name(relation_prop_name)
                    if not relation_prop:
                        issues.append(f"Rollup property '{prop_name}' references non-existent relation property '{relation_prop_name}'")
                    elif relation_prop.type != "relation":
                        issues.append(f"Rollup property '{prop_name}' references non-relation property '{relation_prop_name}'")
        
        return issues
    
    def _validate_cross_database_consistency(self, workspace: WorkspaceSchema) -> List[str]:
        """Validate consistency across databases."""
        issues = []
        
        # Check that all relation targets exist
        for db_id, schema in workspace.databases.items():
            for prop_name, prop_def in schema.relation_properties.items():
                target_db_id = prop_def.relation_database_id
                if target_db_id and target_db_id not in workspace.databases:
                    issues.append(f"Database '{schema.title}' relation property '{prop_name}' references non-existent database: {target_db_id}")
        
        return issues
    
    def _validate_relationships(self, workspace: WorkspaceSchema) -> List[str]:
        """Validate relationship consistency."""
        issues = []
        
        for relationship in workspace.relationships:
            source_db = workspace.get_database(relationship.source_database_id)
            target_db = workspace.get_database(relationship.target_database_id)
            
            if not source_db:
                issues.append(f"Relationship references non-existent source database: {relationship.source_database_id}")
                continue
            
            if not target_db:
                issues.append(f"Relationship references non-existent target database: {relationship.target_database_id}")
                continue
            
            # Validate source property
            source_prop = source_db.get_property_by_name(relationship.source_property_name)
            if not source_prop:
                issues.append(f"Relationship references non-existent property '{relationship.source_property_name}' in database '{source_db.title}'")
            elif source_prop.type != "relation":
                issues.append(f"Relationship property '{relationship.source_property_name}' in database '{source_db.title}' is not a relation type")
            elif source_prop.relation_database_id != relationship.target_database_id:
                issues.append(f"Relationship property '{relationship.source_property_name}' points to wrong database")
            
            # Validate bidirectional relationship if specified
            if relationship.target_property_name:
                target_prop = target_db.get_property_by_name(relationship.target_property_name)
                if not target_prop:
                    issues.append(f"Bidirectional relationship references non-existent property '{relationship.target_property_name}' in database '{target_db.title}'")
                elif target_prop.type != "relation":
                    issues.append(f"Bidirectional relationship property '{relationship.target_property_name}' in database '{target_db.title}' is not a relation type")
                elif target_prop.relation_database_id != relationship.source_database_id:
                    issues.append(f"Bidirectional relationship property '{relationship.target_property_name}' points to wrong database")
        
        return issues
    
    def _validate_naming_conventions(self, workspace: WorkspaceSchema) -> List[str]:
        """Validate naming conventions."""
        issues = []
        
        # Check for duplicate database titles
        titles = {}
        for db_id, schema in workspace.databases.items():
            title_lower = schema.title.lower()
            if title_lower in titles:
                issues.append(f"Duplicate database title: '{schema.title}' (conflicts with database {titles[title_lower]})")
            titles[title_lower] = db_id
        
        # Check for problematic characters in names
        problematic_chars = set("!@#$%^&*()+={}[]|\\:;\"'<>?,./")
        
        for db_id, schema in workspace.databases.items():
            # Check database title
            if any(char in schema.title for char in problematic_chars):
                issues.append(f"Database title '{schema.title}' contains problematic characters")
            
            # Check property names
            for prop_name in schema.properties.keys():
                if any(char in prop_name for char in problematic_chars):
                    issues.append(f"Property name '{prop_name}' in database '{schema.title}' contains problematic characters")
        
        return issues
    
    def validate_for_code_generation(self, workspace: WorkspaceSchema) -> List[str]:
        """Validate workspace schema for code generation readiness."""
        issues = []
        
        # Standard validation first
        issues.extend(self.validate_workspace_schema(workspace))
        
        # Code generation specific validation
        python_keywords = {
            "False", "None", "True", "and", "as", "assert", "break", "class",
            "continue", "def", "del", "elif", "else", "except", "finally",
            "for", "from", "global", "if", "import", "in", "is", "lambda",
            "nonlocal", "not", "or", "pass", "raise", "return", "try",
            "while", "with", "yield"
        }
        
        for db_id, schema in workspace.databases.items():
            # Check if database name would conflict with Python keywords
            db_name = self._normalize_name(schema.title)
            if db_name in python_keywords:
                issues.append(f"Database name '{schema.title}' conflicts with Python keyword")
            
            # Check property names
            for prop_name in schema.properties.keys():
                normalized_prop = self._normalize_name(prop_name)
                if normalized_prop in python_keywords:
                    issues.append(f"Property name '{prop_name}' in database '{schema.title}' conflicts with Python keyword")
                
                # Check for names that would cause issues in generated code
                if normalized_prop in {"id", "type", "object", "class", "dict", "list", "str", "int", "float", "bool"}:
                    issues.append(f"Property name '{prop_name}' in database '{schema.title}' conflicts with Python built-in")
        
        return issues
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for code generation."""
        return name.lower().replace(" ", "_").replace("-", "_")
