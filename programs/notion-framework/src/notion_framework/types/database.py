"""Database schema types and structures."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PropertyDefinition(BaseModel):
    """Definition of a property in a Notion database."""
    
    id: str
    name: str
    type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Type-specific configurations
    select_options: Optional[List[Dict[str, Any]]] = None
    multi_select_options: Optional[List[Dict[str, Any]]] = None
    relation_database_id: Optional[str] = None
    rollup_config: Optional[Dict[str, Any]] = None
    formula_expression: Optional[str] = None
    
    @property
    def is_editable(self) -> bool:
        """Check if this property can be edited."""
        readonly_types = {
            "created_time", "created_by", "last_edited_time",
            "last_edited_by", "formula", "rollup", "unique_id"
        }
        return self.type not in readonly_types
    
    @property
    def is_required(self) -> bool:
        """Check if this property is required."""
        # Title properties are always required
        return self.type == "title"


class DatabaseSchema(BaseModel):
    """Complete schema of a Notion database."""
    
    id: str
    title: str
    description: Optional[str] = None
    url: str
    
    # Properties
    properties: Dict[str, PropertyDefinition] = Field(default_factory=dict)
    
    # Parent information
    parent_type: Optional[str] = None
    parent_id: Optional[str] = None
    
    # Metadata
    created_time: Optional[str] = None
    last_edited_time: Optional[str] = None
    archived: bool = False
    is_inline: bool = False
    
    @property
    def title_property(self) -> Optional[PropertyDefinition]:
        """Get the title property."""
        for prop in self.properties.values():
            if prop.type == "title":
                return prop
        return None
    
    @property
    def editable_properties(self) -> Dict[str, PropertyDefinition]:
        """Get all editable properties."""
        return {
            name: prop for name, prop in self.properties.items()
            if prop.is_editable
        }
    
    @property
    def required_properties(self) -> Dict[str, PropertyDefinition]:
        """Get all required properties."""
        return {
            name: prop for name, prop in self.properties.items()
            if prop.is_required
        }
    
    @property
    def relation_properties(self) -> Dict[str, PropertyDefinition]:
        """Get all relation properties."""
        return {
            name: prop for name, prop in self.properties.items()
            if prop.type == "relation"
        }
    
    def get_property_by_name(self, name: str) -> Optional[PropertyDefinition]:
        """Get a property by its name."""
        return self.properties.get(name)
    
    def get_property_by_id(self, prop_id: str) -> Optional[PropertyDefinition]:
        """Get a property by its ID."""
        for prop in self.properties.values():
            if prop.id == prop_id:
                return prop
        return None
    
    @classmethod
    def from_notion_response(cls, response: Dict[str, Any]) -> "DatabaseSchema":
        """Create schema from Notion API response."""
        # Extract title
        title_objects = response.get("title", [])
        title = "".join(t.get("plain_text", "") for t in title_objects)
        
        # Extract description
        description_objects = response.get("description", [])
        description = "".join(d.get("plain_text", "") for d in description_objects)
        
        # Parse properties
        properties = {}
        for prop_name, prop_data in response.get("properties", {}).items():
            prop_def = PropertyDefinition(
                id=prop_data.get("id", ""),
                name=prop_name,
                type=prop_data.get("type", ""),
                config=prop_data
            )
            
            # Extract type-specific data
            if prop_def.type == "select" and "select" in prop_data:
                prop_def.select_options = prop_data["select"].get("options", [])
            elif prop_def.type == "multi_select" and "multi_select" in prop_data:
                prop_def.multi_select_options = prop_data["multi_select"].get("options", [])
            elif prop_def.type == "relation" and "relation" in prop_data:
                prop_def.relation_database_id = prop_data["relation"].get("database_id")
            elif prop_def.type == "rollup" and "rollup" in prop_data:
                prop_def.rollup_config = prop_data["rollup"]
            elif prop_def.type == "formula" and "formula" in prop_data:
                prop_def.formula_expression = prop_data["formula"].get("expression")
            
            properties[prop_name] = prop_def
        
        # Extract parent info
        parent = response.get("parent", {})
        parent_type = parent.get("type")
        parent_id = None
        if parent_type == "page_id":
            parent_id = parent.get("page_id")
        elif parent_type == "workspace":
            parent_id = "workspace"
        
        return cls(
            id=response["id"],
            title=title,
            description=description if description else None,
            url=response.get("url", ""),
            properties=properties,
            parent_type=parent_type,
            parent_id=parent_id,
            created_time=response.get("created_time"),
            last_edited_time=response.get("last_edited_time"),
            archived=response.get("archived", False),
            is_inline=response.get("is_inline", False),
        )


class DatabaseRelationship(BaseModel):
    """Represents a relationship between two databases."""
    
    source_database_id: str
    target_database_id: str
    source_property_name: str
    target_property_name: Optional[str] = None  # For bidirectional relations
    relation_type: str = "one_to_many"  # one_to_one, one_to_many, many_to_many


class WorkspaceSchema(BaseModel):
    """Complete schema of a Notion workspace."""
    
    databases: Dict[str, DatabaseSchema] = Field(default_factory=dict)
    relationships: List[DatabaseRelationship] = Field(default_factory=list)
    
    def add_database(self, schema: DatabaseSchema) -> None:
        """Add a database schema."""
        self.databases[schema.id] = schema
    
    def get_database(self, database_id: str) -> Optional[DatabaseSchema]:
        """Get a database schema by ID."""
        return self.databases.get(database_id)
    
    def get_database_by_name(self, name: str) -> Optional[DatabaseSchema]:
        """Get a database schema by name."""
        for db in self.databases.values():
            if db.title.lower() == name.lower():
                return db
        return None
    
    def discover_relationships(self) -> None:
        """Discover relationships between databases."""
        relationships = []
        
        for source_db in self.databases.values():
            for prop_name, prop_def in source_db.relation_properties.items():
                if prop_def.relation_database_id:
                    target_db = self.get_database(prop_def.relation_database_id)
                    if target_db:
                        # Check for bidirectional relationship
                        reverse_prop = None
                        for target_prop_name, target_prop in target_db.relation_properties.items():
                            if target_prop.relation_database_id == source_db.id:
                                reverse_prop = target_prop_name
                                break
                        
                        relationship = DatabaseRelationship(
                            source_database_id=source_db.id,
                            target_database_id=target_db.id,
                            source_property_name=prop_name,
                            target_property_name=reverse_prop,
                        )
                        relationships.append(relationship)
        
        self.relationships = relationships
    
    @property
    def database_count(self) -> int:
        """Get the number of databases."""
        return len(self.databases)
    
    @property
    def relationship_count(self) -> int:
        """Get the number of relationships."""
        return len(self.relationships)
