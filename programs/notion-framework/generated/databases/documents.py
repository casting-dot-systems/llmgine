"""Generated database class for Documents."""

from datetime import datetime
from notion_framework.types.properties import NotionCheckbox, NotionLastEditedBy, NotionPeople, NotionRelation, NotionStatus, NotionTitle
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union

from notion_framework.client.client import NotionClient
from notion_framework.types.page import DatabasePage, PageData
from notion_framework.types.filters import FilterBuilder, FilterCondition
from notion_framework.types.sorts import SortBuilder, SortCondition


class Documents(BaseModel):
    """Typed interface for Documents database."""
    
    # Database metadata
    database_id: str = "55909df8-1f56-40c4-9327-bab99b4f97f5"
    title: str = "Documents"
    
    # Properties
    events_projects: List[str] = None = Field(
        description="Events/Projects",
    )
    parent_item: List[str] = None = Field(
        description="Parent item",
    )
    google_drive_file: List[str] = None = Field(
        description="Google Drive File",
    )
    person: List[str] = None = Field(
        description="Person",
    )
    contributors: List[str] = None = Field(
        description="Contributors",
    )
    team: List[str] = None = Field(
        description="Team",
    )
    pinned: bool = None = Field(
        description="Pinned",
    )
    owned_by: List[str] = None = Field(
        description="Owned By",
    )
    sub_item: List[str] = None = Field(
        description="Sub-item",
    )
    name: str = Field(
        description="Name",
    )
    in_charge: List[str] = None = Field(
        description="In Charge",
    )
    status: Optional[str] = None = Field(
        description="Status",
    )

    # Internal Notion property objects
    _events_projects_notion: Optional[NotionRelation] = None
    _parent_item_notion: Optional[NotionRelation] = None
    _last_edited_by_notion: Optional[NotionLastEditedBy] = None
    _google_drive_file_notion: Optional[NotionRelation] = None
    _person_notion: Optional[NotionPeople] = None
    _contributors_notion: Optional[NotionPeople] = None
    _team_notion: Optional[NotionRelation] = None
    _pinned_notion: Optional[NotionCheckbox] = None
    _owned_by_notion: Optional[NotionPeople] = None
    _sub_item_notion: Optional[NotionRelation] = None
    _name_notion: Optional[NotionTitle] = None
    _in_charge_notion: Optional[NotionPeople] = None
    _status_notion: Optional[NotionStatus] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._client: Optional[NotionClient] = None
    
    def set_client(self, client: NotionClient) -> None:
        """Set the Notion client for database operations."""
        self._client = client
    
    # Property getters and setters
    
    def set_events_projects(self, value: List[str]) -> None:
        """Set Events/Projects property."""
        self._events_projects_notion = NotionRelation(value)
        self.events_projects = value
    
    def get_events_projects(self) -> List[str]:
        """Get Events/Projects property value."""
        return self.events_projects
    
    def set_parent_item(self, value: List[str]) -> None:
        """Set Parent item property."""
        self._parent_item_notion = NotionRelation(value)
        self.parent_item = value
    
    def get_parent_item(self) -> List[str]:
        """Get Parent item property value."""
        return self.parent_item
    
    def set_google_drive_file(self, value: List[str]) -> None:
        """Set Google Drive File property."""
        self._google_drive_file_notion = NotionRelation(value)
        self.google_drive_file = value
    
    def get_google_drive_file(self) -> List[str]:
        """Get Google Drive File property value."""
        return self.google_drive_file
    
    def set_person(self, value: List[str]) -> None:
        """Set Person property."""
        self._person_notion = NotionPeople(value)
        self.person = value
    
    def get_person(self) -> List[str]:
        """Get Person property value."""
        return self.person
    
    def set_contributors(self, value: List[str]) -> None:
        """Set Contributors property."""
        self._contributors_notion = NotionPeople(value)
        self.contributors = value
    
    def get_contributors(self) -> List[str]:
        """Get Contributors property value."""
        return self.contributors
    
    def set_team(self, value: List[str]) -> None:
        """Set Team property."""
        self._team_notion = NotionRelation(value)
        self.team = value
    
    def get_team(self) -> List[str]:
        """Get Team property value."""
        return self.team
    
    def set_pinned(self, value: bool) -> None:
        """Set Pinned property."""
        self._pinned_notion = NotionCheckbox(value)
        self.pinned = value
    
    def get_pinned(self) -> bool:
        """Get Pinned property value."""
        return self.pinned
    
    def set_owned_by(self, value: List[str]) -> None:
        """Set Owned By property."""
        self._owned_by_notion = NotionPeople(value)
        self.owned_by = value
    
    def get_owned_by(self) -> List[str]:
        """Get Owned By property value."""
        return self.owned_by
    
    def set_sub_item(self, value: List[str]) -> None:
        """Set Sub-item property."""
        self._sub_item_notion = NotionRelation(value)
        self.sub_item = value
    
    def get_sub_item(self) -> List[str]:
        """Get Sub-item property value."""
        return self.sub_item
    
    def set_name(self, value: str) -> None:
        """Set Name property."""
        self._name_notion = NotionTitle(value)
        self.name = value
    
    def get_name(self) -> str:
        """Get Name property value."""
        return self.name
    
    def set_in_charge(self, value: List[str]) -> None:
        """Set In Charge property."""
        self._in_charge_notion = NotionPeople(value)
        self.in_charge = value
    
    def get_in_charge(self) -> List[str]:
        """Get In Charge property value."""
        return self.in_charge
    
    def set_status(self, value: Optional[str]) -> None:
        """Set Status property."""
        self._status_notion = NotionStatus(value)
        self.status = value
    
    def get_status(self) -> Optional[str]:
        """Get Status property value."""
        return self.status

    def to_notion_properties(self) -> Dict[str, Any]:
        """Convert to Notion API properties format."""
        properties = {}
        
        if self._events_projects_notion is not None:
            properties["Events/Projects"] = self._events_projects_notion.to_notion_format()
        if self._parent_item_notion is not None:
            properties["Parent item"] = self._parent_item_notion.to_notion_format()
        if self._google_drive_file_notion is not None:
            properties["Google Drive File"] = self._google_drive_file_notion.to_notion_format()
        if self._person_notion is not None:
            properties["Person"] = self._person_notion.to_notion_format()
        if self._contributors_notion is not None:
            properties["Contributors"] = self._contributors_notion.to_notion_format()
        if self._team_notion is not None:
            properties["Team"] = self._team_notion.to_notion_format()
        if self._pinned_notion is not None:
            properties["Pinned"] = self._pinned_notion.to_notion_format()
        if self._owned_by_notion is not None:
            properties["Owned By"] = self._owned_by_notion.to_notion_format()
        if self._sub_item_notion is not None:
            properties["Sub-item"] = self._sub_item_notion.to_notion_format()
        if self._name_notion is not None:
            properties["Name"] = self._name_notion.to_notion_format()
        if self._in_charge_notion is not None:
            properties["In Charge"] = self._in_charge_notion.to_notion_format()
        if self._status_notion is not None:
            properties["Status"] = self._status_notion.to_notion_format()
        
        return properties
    
    @classmethod
    def from_page_data(cls, page_data: PageData) -> "Documents":
        """Create instance from Notion page data."""
        instance = cls()
        
        # Extract property values
        events_projects_data = page_data.get_property_value("Events/Projects")
        if events_projects_data:
            instance._events_projects_notion = NotionRelation.from_notion_format(events_projects_data)
            instance.events_projects = instance._events_projects_notion.page_ids
        
        parent_item_data = page_data.get_property_value("Parent item")
        if parent_item_data:
            instance._parent_item_notion = NotionRelation.from_notion_format(parent_item_data)
            instance.parent_item = instance._parent_item_notion.page_ids
        
        last_edited_by_data = page_data.get_property_value("Last edited by")
        if last_edited_by_data:
            instance._last_edited_by_notion = NotionLastEditedBy.from_notion_format(last_edited_by_data)
            instance.last_edited_by = instance._last_edited_by_notion
        
        google_drive_file_data = page_data.get_property_value("Google Drive File")
        if google_drive_file_data:
            instance._google_drive_file_notion = NotionRelation.from_notion_format(google_drive_file_data)
            instance.google_drive_file = instance._google_drive_file_notion.page_ids
        
        person_data = page_data.get_property_value("Person")
        if person_data:
            instance._person_notion = NotionPeople.from_notion_format(person_data)
            instance.person = instance._person_notion.user_ids
        
        contributors_data = page_data.get_property_value("Contributors")
        if contributors_data:
            instance._contributors_notion = NotionPeople.from_notion_format(contributors_data)
            instance.contributors = instance._contributors_notion.user_ids
        
        team_data = page_data.get_property_value("Team")
        if team_data:
            instance._team_notion = NotionRelation.from_notion_format(team_data)
            instance.team = instance._team_notion.page_ids
        
        pinned_data = page_data.get_property_value("Pinned")
        if pinned_data:
            instance._pinned_notion = NotionCheckbox.from_notion_format(pinned_data)
            instance.pinned = instance._pinned_notion.checkbox
        
        owned_by_data = page_data.get_property_value("Owned By")
        if owned_by_data:
            instance._owned_by_notion = NotionPeople.from_notion_format(owned_by_data)
            instance.owned_by = instance._owned_by_notion.user_ids
        
        sub_item_data = page_data.get_property_value("Sub-item")
        if sub_item_data:
            instance._sub_item_notion = NotionRelation.from_notion_format(sub_item_data)
            instance.sub_item = instance._sub_item_notion.page_ids
        
        name_data = page_data.get_property_value("Name")
        if name_data:
            instance._name_notion = NotionTitle.from_notion_format(name_data)
            instance.name = instance._name_notion.plain_text
        
        in_charge_data = page_data.get_property_value("In Charge")
        if in_charge_data:
            instance._in_charge_notion = NotionPeople.from_notion_format(in_charge_data)
            instance.in_charge = instance._in_charge_notion.user_ids
        
        status_data = page_data.get_property_value("Status")
        if status_data:
            instance._status_notion = NotionStatus.from_notion_format(status_data)
            instance.status = instance._status_notion.value
        
        return instance
    
    # CRUD Operations
    
    async def create(self) -> str:
        """Create a new page in the database."""
        if not self._client:
            raise ValueError("Client not set. Call set_client() first.")
        
        page_data = {
            "parent": {"database_id": self.database_id},
            "properties": self.to_notion_properties()
        }
        
        response = await self._client.create_page(**page_data)
        return response["id"]
    
    async def update(self, page_id: str) -> str:
        """Update an existing page."""
        if not self._client:
            raise ValueError("Client not set. Call set_client() first.")
        
        response = await self._client.update_page(
            page_id=page_id,
            properties=self.to_notion_properties()
        )
        return response["id"]
    
    @classmethod
    async def get(cls, client: NotionClient, page_id: str) -> "Documents":
        """Get a page by ID."""
        response = await client.get_page(page_id)
        page_data = PageData.from_notion_response(response)
        
        instance = cls.from_page_data(page_data)
        instance.set_client(client)
        return instance
    
    @classmethod
    async def list(
        cls,
        client: NotionClient,
        filter_condition: Optional[FilterCondition] = None,
        sorts: Optional[List[SortCondition]] = None,
        limit: Optional[int] = None
    ) -> List["Documents"]:
        """List pages from the database."""
        query_params = {
            "database_id": cls.database_id
        }
        
        if filter_condition:
            query_params["filter_obj"] = filter_condition.to_notion_format()
        
        if sorts:
            query_params["sorts"] = [sort.to_notion_format() for sort in sorts]
        
        if limit:
            query_params["page_size"] = limit
        
        response = await client.query_database(**query_params)
        
        instances = []
        for result in response.get("results", []):
            page_data = PageData.from_notion_response(result)
            instance = cls.from_page_data(page_data)
            instance.set_client(client)
            instances.append(instance)
        
        return instances

    # Filter helpers
    
    @classmethod
    def filter(cls) -> FilterBuilder:
        """Get a filter builder for this database."""
        return FilterBuilder()
    
    @classmethod
    def sort(cls) -> SortBuilder:
        """Get a sort builder for this database."""
        return SortBuilder()

    
    # Pinned filter helpers
    @classmethod
    def filter_by_pinned(cls, value: bool) -> FilterCondition:
        """Filter by Pinned."""
        return cls.filter().property("Pinned").checkbox().equals(value)
    
    # Name filter helpers
    @classmethod
    def filter_by_name_contains(cls, value: str) -> FilterCondition:
        """Filter by Name containing value."""
        return cls.filter().property("Name").title().contains(value)
