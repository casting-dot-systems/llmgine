"""Generated database class for Teams."""

from datetime import datetime
from notion_framework.types.properties import NotionFiles, NotionPeople, NotionRelation, NotionTitle
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union

from notion_framework.client.client import NotionClient
from notion_framework.types.page import DatabasePage, PageData
from notion_framework.types.filters import FilterBuilder, FilterCondition
from notion_framework.types.sorts import SortBuilder, SortCondition


class Teams(BaseModel):
    """Typed interface for Teams database."""
    
    # Database metadata
    database_id: str = "139594e5-2bd9-47af-93ca-bb72a35742d2"
    title: str = "Teams"
    
    # Properties
    __events_projects: List[str] = None = Field(
        description="💥 Events/Projects",
    )
    cover: List[str] = None = Field(
        description="Cover",
    )
    person: List[str] = None = Field(
        description="Person",
    )
    committee: List[str] = None = Field(
        description="Committee",
    )
    document: List[str] = None = Field(
        description="Document",
    )
    name: str = Field(
        description="Name",
    )

    # Internal Notion property objects
    ___events_projects_notion: Optional[NotionRelation] = None
    _cover_notion: Optional[NotionFiles] = None
    _person_notion: Optional[NotionPeople] = None
    _committee_notion: Optional[NotionRelation] = None
    _document_notion: Optional[NotionRelation] = None
    _name_notion: Optional[NotionTitle] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._client: Optional[NotionClient] = None
    
    def set_client(self, client: NotionClient) -> None:
        """Set the Notion client for database operations."""
        self._client = client
    
    # Property getters and setters
    
    def set___events_projects(self, value: List[str]) -> None:
        """Set 💥 Events/Projects property."""
        self.___events_projects_notion = NotionRelation(value)
        self.__events_projects = value
    
    def get___events_projects(self) -> List[str]:
        """Get 💥 Events/Projects property value."""
        return self.__events_projects
    
    def set_cover(self, value: List[str]) -> None:
        """Set Cover property."""
        self._cover_notion = NotionFiles(value)
        self.cover = value
    
    def get_cover(self) -> List[str]:
        """Get Cover property value."""
        return self.cover
    
    def set_person(self, value: List[str]) -> None:
        """Set Person property."""
        self._person_notion = NotionPeople(value)
        self.person = value
    
    def get_person(self) -> List[str]:
        """Get Person property value."""
        return self.person
    
    def set_committee(self, value: List[str]) -> None:
        """Set Committee property."""
        self._committee_notion = NotionRelation(value)
        self.committee = value
    
    def get_committee(self) -> List[str]:
        """Get Committee property value."""
        return self.committee
    
    def set_document(self, value: List[str]) -> None:
        """Set Document property."""
        self._document_notion = NotionRelation(value)
        self.document = value
    
    def get_document(self) -> List[str]:
        """Get Document property value."""
        return self.document
    
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
        
        if self.___events_projects_notion is not None:
            properties["💥 Events/Projects"] = self.___events_projects_notion.to_notion_format()
        if self._cover_notion is not None:
            properties["Cover"] = self._cover_notion.to_notion_format()
        if self._person_notion is not None:
            properties["Person"] = self._person_notion.to_notion_format()
        if self._committee_notion is not None:
            properties["Committee"] = self._committee_notion.to_notion_format()
        if self._document_notion is not None:
            properties["Document"] = self._document_notion.to_notion_format()
        if self._name_notion is not None:
            properties["Name"] = self._name_notion.to_notion_format()
        
        return properties
    
    @classmethod
    def from_page_data(cls, page_data: PageData) -> "Teams":
        """Create instance from Notion page data."""
        instance = cls()
        
        # Extract property values
        __events_projects_data = page_data.get_property_value("💥 Events/Projects")
        if __events_projects_data:
            instance.___events_projects_notion = NotionRelation.from_notion_format(__events_projects_data)
            instance.__events_projects = instance.___events_projects_notion.page_ids
        
        cover_data = page_data.get_property_value("Cover")
        if cover_data:
            instance._cover_notion = NotionFiles.from_notion_format(cover_data)
            instance.cover = instance._cover_notion
        
        person_data = page_data.get_property_value("Person")
        if person_data:
            instance._person_notion = NotionPeople.from_notion_format(person_data)
            instance.person = instance._person_notion.user_ids
        
        committee_data = page_data.get_property_value("Committee")
        if committee_data:
            instance._committee_notion = NotionRelation.from_notion_format(committee_data)
            instance.committee = instance._committee_notion.page_ids
        
        document_data = page_data.get_property_value("Document")
        if document_data:
            instance._document_notion = NotionRelation.from_notion_format(document_data)
            instance.document = instance._document_notion.page_ids
        
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
    async def get(cls, client: NotionClient, page_id: str) -> "Teams":
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
    ) -> List["Teams"]:
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

    
    # Name filter helpers
    @classmethod
    def filter_by_name_contains(cls, value: str) -> FilterCondition:
        """Filter by Name containing value."""
        return cls.filter().property("Name").title().contains(value)
