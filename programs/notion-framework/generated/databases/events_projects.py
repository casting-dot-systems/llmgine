"""Generated database class for Events/Projects."""

from datetime import datetime
from notion_framework.types.properties import NotionDate, NotionPeople, NotionRelation, NotionSelect, NotionText, NotionTitle
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union

from notion_framework.client.client import NotionClient
from notion_framework.types.page import DatabasePage, PageData
from notion_framework.types.filters import FilterBuilder, FilterCondition
from notion_framework.types.sorts import SortBuilder, SortCondition


class EventsProjects(BaseModel):
    """Typed interface for Events/Projects database."""
    
    # Database metadata
    database_id: str = "918affd4-ce0d-4b8e-b760-4d972fd24826"
    title: str = "Events/Projects"
    
    # Properties
    parent_item: List[str] = None = Field(
        description="Parent item",
    )
    type: Optional[Literal["Note", "Event", "Project", "Admin", "Program", "Portfolio", "User Story", "Epic", "Sprint", "Feature"]] = None = Field(
        description="Type",
        enum=["Note", "Event", "Project", "Admin", "Program", "Portfolio", "User Story", "Epic", "Sprint", "Feature"],
    )
    owner: List[str] = None = Field(
        description="Owner",
    )
    sub_item: List[str] = None = Field(
        description="Sub-item",
    )
    allocated: List[str] = None = Field(
        description="Allocated",
    )
    team: List[str] = None = Field(
        description="Team",
    )
    text: str = None = Field(
        description="Text",
    )
    progress: Optional[str] = None = Field(
        description="Progress",
        enum=["On-Going", "Proposal", "Approved", "Planning", "In-Progress", "Finished", "Cancelled", "Archive", "Paused", "To-Review", "Complete"],
    )
    priority: Optional[Literal["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]] = None = Field(
        description="Priority",
        enum=["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"],
    )
    description: str = None = Field(
        description="Description",
    )
    due_date_s_: Optional[datetime] = None = Field(
        description="Due Date(s)",
    )
    documents: List[str] = None = Field(
        description="Documents",
    )
    tasks: List[str] = None = Field(
        description="Tasks",
    )
    location: str = None = Field(
        description="Location",
    )
    name: str = Field(
        description="Name",
    )

    # Internal Notion property objects
    _parent_item_notion: Optional[NotionRelation] = None
    _type_notion: Optional[NotionSelect] = None
    _owner_notion: Optional[NotionPeople] = None
    _sub_item_notion: Optional[NotionRelation] = None
    _allocated_notion: Optional[NotionPeople] = None
    _team_notion: Optional[NotionRelation] = None
    _text_notion: Optional[NotionText] = None
    _progress_notion: Optional[NotionSelect] = None
    _priority_notion: Optional[NotionSelect] = None
    _description_notion: Optional[NotionText] = None
    _due_date_s__notion: Optional[NotionDate] = None
    _documents_notion: Optional[NotionRelation] = None
    _tasks_notion: Optional[NotionRelation] = None
    _location_notion: Optional[NotionText] = None
    _name_notion: Optional[NotionTitle] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._client: Optional[NotionClient] = None
    
    def set_client(self, client: NotionClient) -> None:
        """Set the Notion client for database operations."""
        self._client = client
    
    # Property getters and setters
    
    def set_parent_item(self, value: List[str]) -> None:
        """Set Parent item property."""
        self._parent_item_notion = NotionRelation(value)
        self.parent_item = value
    
    def get_parent_item(self) -> List[str]:
        """Get Parent item property value."""
        return self.parent_item
    
    def set_type(self, value: Optional[Literal["Note", "Event", "Project", "Admin", "Program", "Portfolio", "User Story", "Epic", "Sprint", "Feature"]]) -> None:
        """Set Type property."""
        self._type_notion = NotionSelect(value)
        self.type = value
    
    def get_type(self) -> Optional[Literal["Note", "Event", "Project", "Admin", "Program", "Portfolio", "User Story", "Epic", "Sprint", "Feature"]]:
        """Get Type property value."""
        return self.type
    
    def set_owner(self, value: List[str]) -> None:
        """Set Owner property."""
        self._owner_notion = NotionPeople(value)
        self.owner = value
    
    def get_owner(self) -> List[str]:
        """Get Owner property value."""
        return self.owner
    
    def set_sub_item(self, value: List[str]) -> None:
        """Set Sub-item property."""
        self._sub_item_notion = NotionRelation(value)
        self.sub_item = value
    
    def get_sub_item(self) -> List[str]:
        """Get Sub-item property value."""
        return self.sub_item
    
    def set_allocated(self, value: List[str]) -> None:
        """Set Allocated property."""
        self._allocated_notion = NotionPeople(value)
        self.allocated = value
    
    def get_allocated(self) -> List[str]:
        """Get Allocated property value."""
        return self.allocated
    
    def set_team(self, value: List[str]) -> None:
        """Set Team property."""
        self._team_notion = NotionRelation(value)
        self.team = value
    
    def get_team(self) -> List[str]:
        """Get Team property value."""
        return self.team
    
    def set_text(self, value: str) -> None:
        """Set Text property."""
        self._text_notion = NotionText(value)
        self.text = value
    
    def get_text(self) -> str:
        """Get Text property value."""
        return self.text
    
    def set_progress(self, value: Optional[str]) -> None:
        """Set Progress property."""
        self._progress_notion = NotionSelect(value)
        self.progress = value
    
    def get_progress(self) -> Optional[str]:
        """Get Progress property value."""
        return self.progress
    
    def set_priority(self, value: Optional[Literal["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]]) -> None:
        """Set Priority property."""
        self._priority_notion = NotionSelect(value)
        self.priority = value
    
    def get_priority(self) -> Optional[Literal["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]]:
        """Get Priority property value."""
        return self.priority
    
    def set_description(self, value: str) -> None:
        """Set Description property."""
        self._description_notion = NotionText(value)
        self.description = value
    
    def get_description(self) -> str:
        """Get Description property value."""
        return self.description
    
    def set_due_date_s_(self, value: Optional[datetime]) -> None:
        """Set Due Date(s) property."""
        self._due_date_s__notion = NotionDate(value)
        self.due_date_s_ = value
    
    def get_due_date_s_(self) -> Optional[datetime]:
        """Get Due Date(s) property value."""
        return self.due_date_s_
    
    def set_documents(self, value: List[str]) -> None:
        """Set Documents property."""
        self._documents_notion = NotionRelation(value)
        self.documents = value
    
    def get_documents(self) -> List[str]:
        """Get Documents property value."""
        return self.documents
    
    def set_tasks(self, value: List[str]) -> None:
        """Set Tasks property."""
        self._tasks_notion = NotionRelation(value)
        self.tasks = value
    
    def get_tasks(self) -> List[str]:
        """Get Tasks property value."""
        return self.tasks
    
    def set_location(self, value: str) -> None:
        """Set Location property."""
        self._location_notion = NotionText(value)
        self.location = value
    
    def get_location(self) -> str:
        """Get Location property value."""
        return self.location
    
    def set_name(self, value: str) -> None:
        """Set Name property."""
        self._name_notion = NotionTitle(value)
        self.name = value
    
    def get_name(self) -> str:
        """Get Name property value."""
        return self.name

    def to_notion_properties(self) -> Dict[str, Any]:
        """Convert to Notion API properties format."""
        properties = {}
        
        if self._parent_item_notion is not None:
            properties["Parent item"] = self._parent_item_notion.to_notion_format()
        if self._type_notion is not None:
            properties["Type"] = self._type_notion.to_notion_format()
        if self._owner_notion is not None:
            properties["Owner"] = self._owner_notion.to_notion_format()
        if self._sub_item_notion is not None:
            properties["Sub-item"] = self._sub_item_notion.to_notion_format()
        if self._allocated_notion is not None:
            properties["Allocated"] = self._allocated_notion.to_notion_format()
        if self._team_notion is not None:
            properties["Team"] = self._team_notion.to_notion_format()
        if self._text_notion is not None:
            properties["Text"] = self._text_notion.to_notion_format()
        if self._progress_notion is not None:
            properties["Progress"] = self._progress_notion.to_notion_format()
        if self._priority_notion is not None:
            properties["Priority"] = self._priority_notion.to_notion_format()
        if self._description_notion is not None:
            properties["Description"] = self._description_notion.to_notion_format()
        if self._due_date_s__notion is not None:
            properties["Due Date(s)"] = self._due_date_s__notion.to_notion_format()
        if self._documents_notion is not None:
            properties["Documents"] = self._documents_notion.to_notion_format()
        if self._tasks_notion is not None:
            properties["Tasks"] = self._tasks_notion.to_notion_format()
        if self._location_notion is not None:
            properties["Location"] = self._location_notion.to_notion_format()
        if self._name_notion is not None:
            properties["Name"] = self._name_notion.to_notion_format()
        
        return properties
    
    @classmethod
    def from_page_data(cls, page_data: PageData) -> "EventsProjects":
        """Create instance from Notion page data."""
        instance = cls()
        
        # Extract property values
        parent_item_data = page_data.get_property_value("Parent item")
        if parent_item_data:
            instance._parent_item_notion = NotionRelation.from_notion_format(parent_item_data)
            instance.parent_item = instance._parent_item_notion.page_ids
        
        type_data = page_data.get_property_value("Type")
        if type_data:
            instance._type_notion = NotionSelect.from_notion_format(type_data)
            instance.type = instance._type_notion.value
        
        owner_data = page_data.get_property_value("Owner")
        if owner_data:
            instance._owner_notion = NotionPeople.from_notion_format(owner_data)
            instance.owner = instance._owner_notion.user_ids
        
        sub_item_data = page_data.get_property_value("Sub-item")
        if sub_item_data:
            instance._sub_item_notion = NotionRelation.from_notion_format(sub_item_data)
            instance.sub_item = instance._sub_item_notion.page_ids
        
        allocated_data = page_data.get_property_value("Allocated")
        if allocated_data:
            instance._allocated_notion = NotionPeople.from_notion_format(allocated_data)
            instance.allocated = instance._allocated_notion.user_ids
        
        team_data = page_data.get_property_value("Team")
        if team_data:
            instance._team_notion = NotionRelation.from_notion_format(team_data)
            instance.team = instance._team_notion.page_ids
        
        text_data = page_data.get_property_value("Text")
        if text_data:
            instance._text_notion = NotionText.from_notion_format(text_data)
            instance.text = instance._text_notion.plain_text
        
        progress_data = page_data.get_property_value("Progress")
        if progress_data:
            instance._progress_notion = NotionSelect.from_notion_format(progress_data)
            instance.progress = instance._progress_notion.value
        
        priority_data = page_data.get_property_value("Priority")
        if priority_data:
            instance._priority_notion = NotionSelect.from_notion_format(priority_data)
            instance.priority = instance._priority_notion.value
        
        description_data = page_data.get_property_value("Description")
        if description_data:
            instance._description_notion = NotionText.from_notion_format(description_data)
            instance.description = instance._description_notion.plain_text
        
        due_date_s__data = page_data.get_property_value("Due Date(s)")
        if due_date_s__data:
            instance._due_date_s__notion = NotionDate.from_notion_format(due_date_s__data)
            instance.due_date_s_ = instance._due_date_s__notion.start_date
        
        documents_data = page_data.get_property_value("Documents")
        if documents_data:
            instance._documents_notion = NotionRelation.from_notion_format(documents_data)
            instance.documents = instance._documents_notion.page_ids
        
        tasks_data = page_data.get_property_value("Tasks")
        if tasks_data:
            instance._tasks_notion = NotionRelation.from_notion_format(tasks_data)
            instance.tasks = instance._tasks_notion.page_ids
        
        location_data = page_data.get_property_value("Location")
        if location_data:
            instance._location_notion = NotionText.from_notion_format(location_data)
            instance.location = instance._location_notion.plain_text
        
        name_data = page_data.get_property_value("Name")
        if name_data:
            instance._name_notion = NotionTitle.from_notion_format(name_data)
            instance.name = instance._name_notion.plain_text
        
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
    async def get(cls, client: NotionClient, page_id: str) -> "EventsProjects":
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
    ) -> List["EventsProjects"]:
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

    
    # Type filter helpers
    @classmethod
    def filter_by_type(cls, value: str) -> FilterCondition:
        """Filter by Type."""
        return cls.filter().property("Type").select().equals(value)
    
    # Text filter helpers
    @classmethod
    def filter_by_text_contains(cls, value: str) -> FilterCondition:
        """Filter by Text containing value."""
        return cls.filter().property("Text").rich_text().contains(value)
    
    # Progress filter helpers
    @classmethod
    def filter_by_progress(cls, value: str) -> FilterCondition:
        """Filter by Progress."""
        return cls.filter().property("Progress").select().equals(value)
    
    # Priority filter helpers
    @classmethod
    def filter_by_priority(cls, value: str) -> FilterCondition:
        """Filter by Priority."""
        return cls.filter().property("Priority").select().equals(value)
    
    # Description filter helpers
    @classmethod
    def filter_by_description_contains(cls, value: str) -> FilterCondition:
        """Filter by Description containing value."""
        return cls.filter().property("Description").rich_text().contains(value)
    
    # Due Date(s) filter helpers
    @classmethod
    def filter_by_due_date_s__past_week(cls) -> FilterCondition:
        """Filter by Due Date(s) in past week."""
        return cls.filter().property("Due Date(s)").date().past_week()
    
    @classmethod
    def filter_by_due_date_s__after(cls, date: Union[str, datetime]) -> FilterCondition:
        """Filter by Due Date(s) after date."""
        return cls.filter().property("Due Date(s)").date().after(date)
    
    # Location filter helpers
    @classmethod
    def filter_by_location_contains(cls, value: str) -> FilterCondition:
        """Filter by Location containing value."""
        return cls.filter().property("Location").rich_text().contains(value)
    
    # Name filter helpers
    @classmethod
    def filter_by_name_contains(cls, value: str) -> FilterCondition:
        """Filter by Name containing value."""
        return cls.filter().property("Name").title().contains(value)
