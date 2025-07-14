"""Generated database class for Meetings and Tasks."""

from datetime import datetime
from notion_framework.types.properties import NotionDate, NotionFormula, NotionLastEditedBy, NotionLastEditedTime, NotionPeople, NotionRelation, NotionSelect, NotionStatus, NotionText, NotionTitle
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union

from notion_framework.client.client import NotionClient
from notion_framework.types.page import DatabasePage, PageData
from notion_framework.types.filters import FilterBuilder, FilterCondition
from notion_framework.types.sorts import SortBuilder, SortCondition


class MeetingsAndTasks(BaseModel):
    """Typed interface for Meetings and Tasks database."""
    
    # Database metadata
    database_id: str = "ed8ba37a-719a-47d7-a796-c2d373c794b9"
    title: str = "Meetings and Tasks"
    
    # Properties
    status: Optional[str] = None = Field(
        description="Status",
    )
    blocking: List[str] = None = Field(
        description="Blocking",
    )
    due_dates: Optional[datetime] = None = Field(
        description="Due Dates",
    )
    parent_task: List[str] = None = Field(
        description="Parent task",
    )
    blocked_by: List[str] = None = Field(
        description="Blocked by",
    )
    sub_task: List[str] = None = Field(
        description="Sub-task",
    )
    in_charge: List[str] = None = Field(
        description="In Charge",
    )
    task_progress: str = None = Field(
        description="Task Progress",
    )
    event_project: List[str] = None = Field(
        description="Event/Project",
    )
    team: List[str] = None = Field(
        description="Team",
    )
    name: str = Field(
        description="Name",
    )
    priority: Optional[Literal["Low", "Medium", "High"]] = None = Field(
        description="Priority",
        enum=["Low", "Medium", "High"],
    )
    description: str = None = Field(
        description="Description",
    )

    # Internal Notion property objects
    _due_date_notion: Optional[NotionFormula] = None
    _status_notion: Optional[NotionStatus] = None
    _blocking_notion: Optional[NotionRelation] = None
    _due_dates_notion: Optional[NotionDate] = None
    _parent_task_notion: Optional[NotionRelation] = None
    _blocked_by_notion: Optional[NotionRelation] = None
    _last_edited_time_notion: Optional[NotionLastEditedTime] = None
    _sub_task_notion: Optional[NotionRelation] = None
    _in_charge_notion: Optional[NotionPeople] = None
    _is_due__notion: Optional[NotionFormula] = None
    _task_progress_notion: Optional[NotionText] = None
    _last_edited_by_notion: Optional[NotionLastEditedBy] = None
    _event_project_notion: Optional[NotionRelation] = None
    _team_notion: Optional[NotionRelation] = None
    _name_notion: Optional[NotionTitle] = None
    _priority_notion: Optional[NotionSelect] = None
    _description_notion: Optional[NotionText] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._client: Optional[NotionClient] = None
    
    def set_client(self, client: NotionClient) -> None:
        """Set the Notion client for database operations."""
        self._client = client
    
    # Property getters and setters
    
    def set_status(self, value: Optional[str]) -> None:
        """Set Status property."""
        self._status_notion = NotionStatus(value)
        self.status = value
    
    def get_status(self) -> Optional[str]:
        """Get Status property value."""
        return self.status
    
    def set_blocking(self, value: List[str]) -> None:
        """Set Blocking property."""
        self._blocking_notion = NotionRelation(value)
        self.blocking = value
    
    def get_blocking(self) -> List[str]:
        """Get Blocking property value."""
        return self.blocking
    
    def set_due_dates(self, value: Optional[datetime]) -> None:
        """Set Due Dates property."""
        self._due_dates_notion = NotionDate(value)
        self.due_dates = value
    
    def get_due_dates(self) -> Optional[datetime]:
        """Get Due Dates property value."""
        return self.due_dates
    
    def set_parent_task(self, value: List[str]) -> None:
        """Set Parent task property."""
        self._parent_task_notion = NotionRelation(value)
        self.parent_task = value
    
    def get_parent_task(self) -> List[str]:
        """Get Parent task property value."""
        return self.parent_task
    
    def set_blocked_by(self, value: List[str]) -> None:
        """Set Blocked by property."""
        self._blocked_by_notion = NotionRelation(value)
        self.blocked_by = value
    
    def get_blocked_by(self) -> List[str]:
        """Get Blocked by property value."""
        return self.blocked_by
    
    def set_sub_task(self, value: List[str]) -> None:
        """Set Sub-task property."""
        self._sub_task_notion = NotionRelation(value)
        self.sub_task = value
    
    def get_sub_task(self) -> List[str]:
        """Get Sub-task property value."""
        return self.sub_task
    
    def set_in_charge(self, value: List[str]) -> None:
        """Set In Charge property."""
        self._in_charge_notion = NotionPeople(value)
        self.in_charge = value
    
    def get_in_charge(self) -> List[str]:
        """Get In Charge property value."""
        return self.in_charge
    
    def set_task_progress(self, value: str) -> None:
        """Set Task Progress property."""
        self._task_progress_notion = NotionText(value)
        self.task_progress = value
    
    def get_task_progress(self) -> str:
        """Get Task Progress property value."""
        return self.task_progress
    
    def set_event_project(self, value: List[str]) -> None:
        """Set Event/Project property."""
        self._event_project_notion = NotionRelation(value)
        self.event_project = value
    
    def get_event_project(self) -> List[str]:
        """Get Event/Project property value."""
        return self.event_project
    
    def set_team(self, value: List[str]) -> None:
        """Set Team property."""
        self._team_notion = NotionRelation(value)
        self.team = value
    
    def get_team(self) -> List[str]:
        """Get Team property value."""
        return self.team
    
    def set_name(self, value: str) -> None:
        """Set Name property."""
        self._name_notion = NotionTitle(value)
        self.name = value
    
    def get_name(self) -> str:
        """Get Name property value."""
        return self.name
    
    def set_priority(self, value: Optional[Literal["Low", "Medium", "High"]]) -> None:
        """Set Priority property."""
        self._priority_notion = NotionSelect(value)
        self.priority = value
    
    def get_priority(self) -> Optional[Literal["Low", "Medium", "High"]]:
        """Get Priority property value."""
        return self.priority
    
    def set_description(self, value: str) -> None:
        """Set Description property."""
        self._description_notion = NotionText(value)
        self.description = value
    
    def get_description(self) -> str:
        """Get Description property value."""
        return self.description

    def to_notion_properties(self) -> Dict[str, Any]:
        """Convert to Notion API properties format."""
        properties = {}
        
        if self._status_notion is not None:
            properties["Status"] = self._status_notion.to_notion_format()
        if self._blocking_notion is not None:
            properties["Blocking"] = self._blocking_notion.to_notion_format()
        if self._due_dates_notion is not None:
            properties["Due Dates"] = self._due_dates_notion.to_notion_format()
        if self._parent_task_notion is not None:
            properties["Parent task"] = self._parent_task_notion.to_notion_format()
        if self._blocked_by_notion is not None:
            properties["Blocked by"] = self._blocked_by_notion.to_notion_format()
        if self._sub_task_notion is not None:
            properties["Sub-task"] = self._sub_task_notion.to_notion_format()
        if self._in_charge_notion is not None:
            properties["In Charge"] = self._in_charge_notion.to_notion_format()
        if self._task_progress_notion is not None:
            properties["Task Progress"] = self._task_progress_notion.to_notion_format()
        if self._event_project_notion is not None:
            properties["Event/Project"] = self._event_project_notion.to_notion_format()
        if self._team_notion is not None:
            properties["Team"] = self._team_notion.to_notion_format()
        if self._name_notion is not None:
            properties["Name"] = self._name_notion.to_notion_format()
        if self._priority_notion is not None:
            properties["Priority"] = self._priority_notion.to_notion_format()
        if self._description_notion is not None:
            properties["Description"] = self._description_notion.to_notion_format()
        
        return properties
    
    @classmethod
    def from_page_data(cls, page_data: PageData) -> "MeetingsAndTasks":
        """Create instance from Notion page data."""
        instance = cls()
        
        # Extract property values
        due_date_data = page_data.get_property_value("Due Date")
        if due_date_data:
            instance._due_date_notion = NotionFormula.from_notion_format(due_date_data)
            instance.due_date = instance._due_date_notion
        
        status_data = page_data.get_property_value("Status")
        if status_data:
            instance._status_notion = NotionStatus.from_notion_format(status_data)
            instance.status = instance._status_notion.value
        
        blocking_data = page_data.get_property_value("Blocking")
        if blocking_data:
            instance._blocking_notion = NotionRelation.from_notion_format(blocking_data)
            instance.blocking = instance._blocking_notion.page_ids
        
        due_dates_data = page_data.get_property_value("Due Dates")
        if due_dates_data:
            instance._due_dates_notion = NotionDate.from_notion_format(due_dates_data)
            instance.due_dates = instance._due_dates_notion.start_date
        
        parent_task_data = page_data.get_property_value("Parent task")
        if parent_task_data:
            instance._parent_task_notion = NotionRelation.from_notion_format(parent_task_data)
            instance.parent_task = instance._parent_task_notion.page_ids
        
        blocked_by_data = page_data.get_property_value("Blocked by")
        if blocked_by_data:
            instance._blocked_by_notion = NotionRelation.from_notion_format(blocked_by_data)
            instance.blocked_by = instance._blocked_by_notion.page_ids
        
        last_edited_time_data = page_data.get_property_value("Last edited time")
        if last_edited_time_data:
            instance._last_edited_time_notion = NotionLastEditedTime.from_notion_format(last_edited_time_data)
            instance.last_edited_time = instance._last_edited_time_notion
        
        sub_task_data = page_data.get_property_value("Sub-task")
        if sub_task_data:
            instance._sub_task_notion = NotionRelation.from_notion_format(sub_task_data)
            instance.sub_task = instance._sub_task_notion.page_ids
        
        in_charge_data = page_data.get_property_value("In Charge")
        if in_charge_data:
            instance._in_charge_notion = NotionPeople.from_notion_format(in_charge_data)
            instance.in_charge = instance._in_charge_notion.user_ids
        
        is_due__data = page_data.get_property_value("Is Due ")
        if is_due__data:
            instance._is_due__notion = NotionFormula.from_notion_format(is_due__data)
            instance.is_due_ = instance._is_due__notion
        
        task_progress_data = page_data.get_property_value("Task Progress")
        if task_progress_data:
            instance._task_progress_notion = NotionText.from_notion_format(task_progress_data)
            instance.task_progress = instance._task_progress_notion.plain_text
        
        last_edited_by_data = page_data.get_property_value("Last edited by")
        if last_edited_by_data:
            instance._last_edited_by_notion = NotionLastEditedBy.from_notion_format(last_edited_by_data)
            instance.last_edited_by = instance._last_edited_by_notion
        
        event_project_data = page_data.get_property_value("Event/Project")
        if event_project_data:
            instance._event_project_notion = NotionRelation.from_notion_format(event_project_data)
            instance.event_project = instance._event_project_notion.page_ids
        
        team_data = page_data.get_property_value("Team")
        if team_data:
            instance._team_notion = NotionRelation.from_notion_format(team_data)
            instance.team = instance._team_notion.page_ids
        
        name_data = page_data.get_property_value("Name")
        if name_data:
            instance._name_notion = NotionTitle.from_notion_format(name_data)
            instance.name = instance._name_notion.plain_text
        
        priority_data = page_data.get_property_value("Priority")
        if priority_data:
            instance._priority_notion = NotionSelect.from_notion_format(priority_data)
            instance.priority = instance._priority_notion.value
        
        description_data = page_data.get_property_value("Description")
        if description_data:
            instance._description_notion = NotionText.from_notion_format(description_data)
            instance.description = instance._description_notion.plain_text
        
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
    async def get(cls, client: NotionClient, page_id: str) -> "MeetingsAndTasks":
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
    ) -> List["MeetingsAndTasks"]:
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

    
    # Due Dates filter helpers
    @classmethod
    def filter_by_due_dates_past_week(cls) -> FilterCondition:
        """Filter by Due Dates in past week."""
        return cls.filter().property("Due Dates").date().past_week()
    
    @classmethod
    def filter_by_due_dates_after(cls, date: Union[str, datetime]) -> FilterCondition:
        """Filter by Due Dates after date."""
        return cls.filter().property("Due Dates").date().after(date)
    
    # Task Progress filter helpers
    @classmethod
    def filter_by_task_progress_contains(cls, value: str) -> FilterCondition:
        """Filter by Task Progress containing value."""
        return cls.filter().property("Task Progress").rich_text().contains(value)
    
    # Name filter helpers
    @classmethod
    def filter_by_name_contains(cls, value: str) -> FilterCondition:
        """Filter by Name containing value."""
        return cls.filter().property("Name").title().contains(value)
    
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
