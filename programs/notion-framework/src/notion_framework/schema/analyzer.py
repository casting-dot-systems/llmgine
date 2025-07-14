"""Schema analysis and database introspection."""

import logging
from typing import Any, Dict, List, Optional

from ..client.client import NotionClient
from ..client.exceptions import SchemaError
from ..types.database import DatabaseSchema, WorkspaceSchema

logger = logging.getLogger(__name__)


class SchemaAnalyzer:
    """Analyzes Notion database schemas and relationships."""
    
    def __init__(self, client: NotionClient):
        self.client = client
        
    async def analyze_database(self, database_id: str) -> DatabaseSchema:
        """Analyze a single database schema."""
        try:
            logger.info(f"Analyzing database schema for {database_id}")
            response = await self.client.get_database(database_id)
            schema = DatabaseSchema.from_notion_response(response)
            
            # Validate schema
            self._validate_database_schema(schema)
            
            logger.info(f"Successfully analyzed database '{schema.title}' with {len(schema.properties)} properties")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to analyze database {database_id}: {e}")
            raise SchemaError(f"Could not analyze database: {e}", database_id)
    
    async def analyze_workspace(self, database_ids: List[str]) -> WorkspaceSchema:
        """Analyze multiple databases and their relationships."""
        logger.info(f"Analyzing workspace with {len(database_ids)} databases")
        
        workspace = WorkspaceSchema()
        
        # Analyze each database
        for db_id in database_ids:
            try:
                schema = await self.analyze_database(db_id)
                workspace.add_database(schema)
                logger.info(f"Added database '{schema.title}' to workspace")
            except Exception as e:
                logger.warning(f"Skipping database {db_id} due to error: {e}")
                continue
        
        # Discover relationships
        workspace.discover_relationships()
        
        logger.info(f"Workspace analysis complete: {workspace.database_count} databases, {workspace.relationship_count} relationships")
        return workspace
    
    async def discover_database_from_url(self, url: str) -> str:
        """Extract database ID from a Notion URL."""
        # Handle different URL formats
        if "/database/" in url:
            # Direct database URL
            return url.split("/database/")[-1].split("?")[0].split("#")[0]
        elif "notion.so/" in url:
            # Page or database URL
            path_part = url.split("notion.so/")[-1]
            # Remove query parameters and fragments
            clean_path = path_part.split("?")[0].split("#")[0]
            # Extract ID (last 32 characters, typically)
            if len(clean_path) >= 32:
                return clean_path[-32:]
            
        raise SchemaError(f"Could not extract database ID from URL: {url}")
    
    async def search_databases(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for databases in the workspace."""
        try:
            search_filter = {"object": "database"}
            response = await self.client.search(
                query=query,
                filter_obj=search_filter
            )
            
            databases = []
            for result in response.get("results", []):
                if result.get("object") == "database":
                    title_objects = result.get("title", [])
                    title = "".join(t.get("plain_text", "") for t in title_objects)
                    
                    databases.append({
                        "id": result["id"],
                        "title": title,
                        "url": result.get("url", ""),
                        "created_time": result.get("created_time"),
                        "last_edited_time": result.get("last_edited_time"),
                    })
            
            logger.info(f"Found {len(databases)} databases")
            return databases
            
        except Exception as e:
            logger.error(f"Failed to search databases: {e}")
            raise SchemaError(f"Database search failed: {e}")
    
    def _validate_database_schema(self, schema: DatabaseSchema) -> None:
        """Validate database schema for completeness."""
        if not schema.title:
            raise SchemaError(f"Database {schema.id} has no title")
        
        if not schema.properties:
            raise SchemaError(f"Database {schema.id} has no properties")
        
        # Check for title property
        title_prop = schema.title_property
        if not title_prop:
            raise SchemaError(f"Database {schema.id} has no title property")
        
        # Validate property types
        supported_types = {
            "title", "rich_text", "number", "select", "multi_select",
            "date", "people", "files", "checkbox", "url", "email",
            "phone_number", "formula", "relation", "rollup",
            "created_time", "created_by", "last_edited_time",
            "last_edited_by", "status", "unique_id"
        }
        
        for prop_name, prop_def in schema.properties.items():
            if prop_def.type not in supported_types:
                logger.warning(f"Unsupported property type '{prop_def.type}' for property '{prop_name}' in database {schema.id}")
    
    def analyze_property_dependencies(self, schema: DatabaseSchema) -> Dict[str, List[str]]:
        """Analyze dependencies between properties."""
        dependencies = {}
        
        for prop_name, prop_def in schema.properties.items():
            deps = []
            
            # Formula properties depend on referenced properties
            if prop_def.type == "formula" and prop_def.formula_expression:
                # Simple property name extraction (could be more sophisticated)
                expression = prop_def.formula_expression
                for other_prop_name in schema.properties.keys():
                    if other_prop_name != prop_name and other_prop_name in expression:
                        deps.append(other_prop_name)
            
            # Rollup properties depend on relation properties
            elif prop_def.type == "rollup" and prop_def.rollup_config:
                relation_prop = prop_def.rollup_config.get("relation_property_name")
                if relation_prop and relation_prop in schema.properties:
                    deps.append(relation_prop)
            
            if deps:
                dependencies[prop_name] = deps
        
        return dependencies
    
    def analyze_property_usage_patterns(self, schema: DatabaseSchema) -> Dict[str, Dict[str, Any]]:
        """Analyze property usage patterns and characteristics."""
        patterns = {}
        
        for prop_name, prop_def in schema.properties.items():
            pattern = {
                "type": prop_def.type,
                "is_editable": prop_def.is_editable,
                "is_required": prop_def.is_required,
                "complexity": "simple",
                "relationships": [],
                "validation_rules": [],
            }
            
            # Determine complexity
            if prop_def.type in ["formula", "rollup"]:
                pattern["complexity"] = "computed"
            elif prop_def.type in ["relation", "people"]:
                pattern["complexity"] = "relational"
            elif prop_def.type in ["multi_select", "files"]:
                pattern["complexity"] = "collection"
            
            # Track relationships
            if prop_def.type == "relation" and prop_def.relation_database_id:
                pattern["relationships"].append({
                    "type": "relation",
                    "target_database": prop_def.relation_database_id
                })
            
            # Extract validation rules for select properties
            if prop_def.type == "select" and prop_def.select_options:
                pattern["validation_rules"].append({
                    "type": "enum",
                    "allowed_values": [opt["name"] for opt in prop_def.select_options]
                })
            elif prop_def.type == "multi_select" and prop_def.multi_select_options:
                pattern["validation_rules"].append({
                    "type": "multi_enum",
                    "allowed_values": [opt["name"] for opt in prop_def.multi_select_options]
                })
            
            patterns[prop_name] = pattern
        
        return patterns
    
    def suggest_tool_functions(self, schema: DatabaseSchema) -> List[Dict[str, Any]]:
        """Suggest tool functions based on database schema."""
        suggestions = []
        
        # Basic CRUD operations
        suggestions.extend([
            {
                "name": f"create_{self._normalize_name(schema.title)}",
                "description": f"Create a new {schema.title}",
                "type": "create",
                "required_properties": list(schema.required_properties.keys()),
                "optional_properties": list(schema.editable_properties.keys())
            },
            {
                "name": f"update_{self._normalize_name(schema.title)}",
                "description": f"Update an existing {schema.title}",
                "type": "update",
                "required_properties": ["page_id"],
                "optional_properties": list(schema.editable_properties.keys())
            },
            {
                "name": f"get_{self._normalize_name(schema.title)}",
                "description": f"Get a {schema.title} by ID",
                "type": "read",
                "required_properties": ["page_id"],
                "optional_properties": []
            },
            {
                "name": f"list_{self._normalize_name(schema.title)}s",
                "description": f"List {schema.title}s with optional filtering",
                "type": "list",
                "required_properties": [],
                "optional_properties": ["limit", "filter", "sort"]
            }
        ])
        
        # Property-specific operations
        for prop_name, prop_def in schema.properties.items():
            if prop_def.type == "select":
                suggestions.append({
                    "name": f"set_{self._normalize_name(schema.title)}_{self._normalize_name(prop_name)}",
                    "description": f"Set {prop_name} for a {schema.title}",
                    "type": "update_property",
                    "required_properties": ["page_id", prop_name],
                    "optional_properties": []
                })
            
            elif prop_def.type == "relation" and prop_def.relation_database_id:
                suggestions.extend([
                    {
                        "name": f"add_{self._normalize_name(schema.title)}_relation",
                        "description": f"Add relation to {prop_name}",
                        "type": "add_relation",
                        "required_properties": ["page_id", "related_page_id"],
                        "optional_properties": []
                    },
                    {
                        "name": f"remove_{self._normalize_name(schema.title)}_relation",
                        "description": f"Remove relation from {prop_name}",
                        "type": "remove_relation",
                        "required_properties": ["page_id", "related_page_id"],
                        "optional_properties": []
                    }
                ])
        
        return suggestions
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for use in function names."""
        return name.lower().replace(" ", "_").replace("-", "_")
    
    async def validate_workspace_consistency(self, workspace: WorkspaceSchema) -> List[str]:
        """Validate workspace for consistency issues."""
        issues = []
        
        # Check for broken relationships
        for relationship in workspace.relationships:
            source_db = workspace.get_database(relationship.source_database_id)
            target_db = workspace.get_database(relationship.target_database_id)
            
            if not source_db:
                issues.append(f"Relationship references missing source database: {relationship.source_database_id}")
                continue
                
            if not target_db:
                issues.append(f"Relationship references missing target database: {relationship.target_database_id}")
                continue
            
            # Check if source property exists
            source_prop = source_db.get_property_by_name(relationship.source_property_name)
            if not source_prop:
                issues.append(f"Relationship references missing property '{relationship.source_property_name}' in database '{source_db.title}'")
            elif source_prop.type != "relation":
                issues.append(f"Property '{relationship.source_property_name}' in database '{source_db.title}' is not a relation property")
            elif source_prop.relation_database_id != relationship.target_database_id:
                issues.append(f"Relation property '{relationship.source_property_name}' points to wrong database")
        
        # Check for naming conflicts
        db_titles = [db.title.lower() for db in workspace.databases.values()]
        if len(set(db_titles)) != len(db_titles):
            issues.append("Multiple databases have the same title")
        
        return issues
