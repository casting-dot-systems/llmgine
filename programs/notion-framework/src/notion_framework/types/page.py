"""Page and block data structures."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .properties import NotionProperty


class PageData(BaseModel):
    """Represents a Notion page."""
    
    id: str
    url: str
    created_time: datetime
    last_edited_time: datetime
    created_by: Dict[str, Any]
    last_edited_by: Dict[str, Any]
    
    # Content
    properties: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Metadata
    archived: bool = False
    in_trash: bool = False
    
    # Parent information
    parent: Dict[str, Any] = Field(default_factory=dict)
    
    # Cover and icon
    cover: Optional[Dict[str, Any]] = None
    icon: Optional[Dict[str, Any]] = None
    
    @property
    def parent_type(self) -> Optional[str]:
        """Get the parent type."""
        return self.parent.get("type")
    
    @property
    def parent_id(self) -> Optional[str]:
        """Get the parent ID."""
        parent_type = self.parent_type
        if parent_type == "database_id":
            return self.parent.get("database_id")
        elif parent_type == "page_id":
            return self.parent.get("page_id")
        elif parent_type == "workspace":
            return "workspace"
        return None
    
    @property
    def is_database_page(self) -> bool:
        """Check if this page belongs to a database."""
        return self.parent_type == "database_id"
    
    def get_property_value(self, property_name: str) -> Optional[Dict[str, Any]]:
        """Get a property value by name."""
        return self.properties.get(property_name)
    
    def get_property_plain_text(self, property_name: str) -> Optional[str]:
        """Get plain text from a property."""
        prop_value = self.get_property_value(property_name)
        if not prop_value:
            return None
        
        prop_type = prop_value.get("type")
        
        if prop_type in ["title", "rich_text"]:
            text_objects = prop_value.get(prop_type, [])
            return "".join(obj.get("plain_text", "") for obj in text_objects)
        elif prop_type == "select":
            select_obj = prop_value.get("select")
            return select_obj.get("name") if select_obj else None
        elif prop_type == "multi_select":
            multi_select = prop_value.get("multi_select", [])
            return ", ".join(obj.get("name", "") for obj in multi_select)
        elif prop_type == "number":
            return str(prop_value.get("number", ""))
        elif prop_type == "checkbox":
            return str(prop_value.get("checkbox", False))
        elif prop_type == "url":
            return prop_value.get("url")
        elif prop_type == "email":
            return prop_value.get("email")
        elif prop_type == "phone_number":
            return prop_value.get("phone_number")
        elif prop_type == "date":
            date_obj = prop_value.get("date")
            if date_obj:
                start = date_obj.get("start", "")
                end = date_obj.get("end")
                return f"{start} - {end}" if end else start
        elif prop_type == "people":
            people = prop_value.get("people", [])
            return ", ".join(person.get("name", "") for person in people)
        elif prop_type == "relation":
            relation = prop_value.get("relation", [])
            return f"{len(relation)} related items"
        
        return None
    
    @classmethod
    def from_notion_response(cls, response: Dict[str, Any]) -> "PageData":
        """Create PageData from Notion API response."""
        return cls(
            id=response["id"],
            url=response["url"],
            created_time=datetime.fromisoformat(response["created_time"]),
            last_edited_time=datetime.fromisoformat(response["last_edited_time"]),
            created_by=response["created_by"],
            last_edited_by=response["last_edited_by"],
            properties=response.get("properties", {}),
            archived=response.get("archived", False),
            in_trash=response.get("in_trash", False),
            parent=response.get("parent", {}),
            cover=response.get("cover"),
            icon=response.get("icon"),
        )


class BlockData(BaseModel):
    """Represents a Notion block."""
    
    id: str
    type: str
    created_time: datetime
    last_edited_time: datetime
    created_by: Dict[str, Any]
    last_edited_by: Dict[str, Any]
    
    # Block content
    content: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    archived: bool = False
    has_children: bool = False
    
    # Parent information
    parent: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def parent_type(self) -> Optional[str]:
        """Get the parent type."""
        return self.parent.get("type")
    
    @property
    def parent_id(self) -> Optional[str]:
        """Get the parent ID."""
        parent_type = self.parent_type
        if parent_type == "page_id":
            return self.parent.get("page_id")
        elif parent_type == "block_id":
            return self.parent.get("block_id")
        return None
    
    @property
    def plain_text(self) -> str:
        """Extract plain text from the block."""
        if self.type == "paragraph":
            rich_text = self.content.get("paragraph", {}).get("rich_text", [])
        elif self.type in ["heading_1", "heading_2", "heading_3"]:
            rich_text = self.content.get(self.type, {}).get("rich_text", [])
        elif self.type == "bulleted_list_item":
            rich_text = self.content.get("bulleted_list_item", {}).get("rich_text", [])
        elif self.type == "numbered_list_item":
            rich_text = self.content.get("numbered_list_item", {}).get("rich_text", [])
        elif self.type == "to_do":
            rich_text = self.content.get("to_do", {}).get("rich_text", [])
        elif self.type == "quote":
            rich_text = self.content.get("quote", {}).get("rich_text", [])
        elif self.type == "code":
            rich_text = self.content.get("code", {}).get("rich_text", [])
        else:
            rich_text = []
        
        return "".join(obj.get("plain_text", "") for obj in rich_text)
    
    @classmethod
    def from_notion_response(cls, response: Dict[str, Any]) -> "BlockData":
        """Create BlockData from Notion API response."""
        block_type = response["type"]
        content = {block_type: response.get(block_type, {})}
        
        return cls(
            id=response["id"],
            type=block_type,
            created_time=datetime.fromisoformat(response["created_time"]),
            last_edited_time=datetime.fromisoformat(response["last_edited_time"]),
            created_by=response["created_by"],
            last_edited_by=response["last_edited_by"],
            content=content,
            archived=response.get("archived", False),
            has_children=response.get("has_children", False),
            parent=response.get("parent", {}),
        )


class DatabasePage(BaseModel):
    """A page that belongs to a database with typed properties."""
    
    page_data: PageData
    database_id: str
    typed_properties: Dict[str, NotionProperty] = Field(default_factory=dict)
    
    def __init__(self, page_data: PageData, database_id: str, **kwargs):
        super().__init__(
            page_data=page_data,
            database_id=database_id,
            **kwargs
        )
    
    @property
    def id(self) -> str:
        """Get the page ID."""
        return self.page_data.id
    
    @property
    def url(self) -> str:
        """Get the page URL."""
        return self.page_data.url
    
    @property
    def created_time(self) -> datetime:
        """Get creation time."""
        return self.page_data.created_time
    
    @property
    def last_edited_time(self) -> datetime:
        """Get last edit time."""
        return self.page_data.last_edited_time
    
    @property
    def archived(self) -> bool:
        """Check if archived."""
        return self.page_data.archived
    
    def get_typed_property(self, property_name: str) -> Optional[NotionProperty]:
        """Get a typed property."""
        return self.typed_properties.get(property_name)
    
    def set_typed_property(self, property_name: str, value: NotionProperty) -> None:
        """Set a typed property."""
        self.typed_properties[property_name] = value
        
    def to_notion_update_format(self) -> Dict[str, Any]:
        """Convert to format for updating the page."""
        properties = {}
        for prop_name, prop_value in self.typed_properties.items():
            properties[prop_name] = prop_value.to_notion_format()
        return {"properties": properties}
