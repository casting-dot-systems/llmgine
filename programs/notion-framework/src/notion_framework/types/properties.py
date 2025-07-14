"""Notion property type definitions with full type safety."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, Union

from pydantic import BaseModel, Field

# Base property types

class NotionProperty(BaseModel, ABC):
    """Base class for all Notion property types."""
    
    @abstractmethod
    def to_notion_format(self) -> Dict[str, Any]:
        """Convert to Notion API format."""
        pass
    
    @classmethod
    @abstractmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionProperty":
        """Create from Notion API response."""
        pass


class RichTextObject(BaseModel):
    """Notion rich text object."""
    type: Literal["text", "mention", "equation"] = "text"
    text: Optional[Dict[str, Any]] = None
    mention: Optional[Dict[str, Any]] = None
    equation: Optional[Dict[str, Any]] = None
    annotations: Dict[str, bool] = Field(default_factory=lambda: {
        "bold": False, "italic": False, "strikethrough": False,
        "underline": False, "code": False
    })
    plain_text: str = ""
    href: Optional[str] = None


# Title property

class NotionTitle(NotionProperty):
    """Notion title property."""
    
    title: List[RichTextObject] = Field(default_factory=list)
    
    def __init__(self, text: Union[str, List[RichTextObject]] = None, **kwargs):
        if isinstance(text, str):
            title = [RichTextObject(
                type="text",
                text={"content": text},
                plain_text=text
            )]
        elif isinstance(text, list):
            title = text
        else:
            title = kwargs.get("title", [])
            
        super().__init__(title=title, **kwargs)
    
    @property
    def plain_text(self) -> str:
        """Get plain text content."""
        return "".join(rt.plain_text for rt in self.title)
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {"title": [rt.dict() for rt in self.title]}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionTitle":
        title_data = data.get("title", [])
        title = [RichTextObject(**item) for item in title_data]
        return cls(title=title)


# Text property

class NotionText(NotionProperty):
    """Notion rich text property."""
    
    rich_text: List[RichTextObject] = Field(default_factory=list)
    
    def __init__(self, text: Union[str, List[RichTextObject]] = None, **kwargs):
        if isinstance(text, str):
            rich_text = [RichTextObject(
                type="text",
                text={"content": text},
                plain_text=text
            )]
        elif isinstance(text, list):
            rich_text = text
        else:
            rich_text = kwargs.get("rich_text", [])
            
        super().__init__(rich_text=rich_text, **kwargs)
    
    @property
    def plain_text(self) -> str:
        """Get plain text content."""
        return "".join(rt.plain_text for rt in self.rich_text)
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {"rich_text": [rt.dict() for rt in self.rich_text]}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionText":
        text_data = data.get("rich_text", [])
        rich_text = [RichTextObject(**item) for item in text_data]
        return cls(rich_text=rich_text)


# Number property

class NotionNumber(NotionProperty):
    """Notion number property."""
    
    number: Optional[Union[int, float]] = None
    
    def __init__(self, value: Optional[Union[int, float]] = None, **kwargs):
        super().__init__(number=value, **kwargs)
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {"number": self.number}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionNumber":
        return cls(number=data.get("number"))


# Select properties

SelectValue = TypeVar("SelectValue", bound=str)

class SelectOption(BaseModel):
    """Notion select option."""
    id: str
    name: str
    color: str


class NotionSelect(NotionProperty, Generic[SelectValue]):
    """Notion select property with type safety."""
    
    select: Optional[SelectOption] = None
    
    def __init__(self, value: Optional[Union[str, SelectOption]] = None, **kwargs):
        if isinstance(value, str):
            select = SelectOption(id="", name=value, color="default")
        elif isinstance(value, SelectOption):
            select = value
        else:
            select = kwargs.get("select")
            
        super().__init__(select=select, **kwargs)
    
    @property
    def value(self) -> Optional[str]:
        """Get the select value."""
        return self.select.name if self.select else None
    
    def to_notion_format(self) -> Dict[str, Any]:
        if self.select:
            return {"select": {"name": self.select.name}}
        return {"select": None}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionSelect":
        select_data = data.get("select")
        if select_data:
            select = SelectOption(**select_data)
        else:
            select = None
        return cls(select=select)


class NotionMultiSelect(NotionProperty):
    """Notion multi-select property."""
    
    multi_select: List[SelectOption] = Field(default_factory=list)
    
    def __init__(self, values: Optional[Union[List[str], List[SelectOption]]] = None, **kwargs):
        if isinstance(values, list) and values and isinstance(values[0], str):
            multi_select = [SelectOption(id="", name=val, color="default") for val in values]
        elif isinstance(values, list):
            multi_select = values
        else:
            multi_select = kwargs.get("multi_select", [])
            
        super().__init__(multi_select=multi_select, **kwargs)
    
    @property
    def values(self) -> List[str]:
        """Get the select values."""
        return [opt.name for opt in self.multi_select]
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {"multi_select": [{"name": opt.name} for opt in self.multi_select]}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionMultiSelect":
        multi_select_data = data.get("multi_select", [])
        multi_select = [SelectOption(**item) for item in multi_select_data]
        return cls(multi_select=multi_select)


# Date property

class NotionDateRange(BaseModel):
    """Notion date range."""
    start: datetime
    end: Optional[datetime] = None
    time_zone: Optional[str] = None


class NotionDate(NotionProperty):
    """Notion date property."""
    
    date: Optional[NotionDateRange] = None
    
    def __init__(self, date: Optional[Union[datetime, NotionDateRange, str]] = None, **kwargs):
        if isinstance(date, datetime):
            date_range = NotionDateRange(start=date)
        elif isinstance(date, str):
            date_range = NotionDateRange(start=datetime.fromisoformat(date))
        elif isinstance(date, NotionDateRange):
            date_range = date
        else:
            date_range = kwargs.get("date")
            
        super().__init__(date=date_range, **kwargs)
    
    @property
    def start_date(self) -> Optional[datetime]:
        """Get start date."""
        return self.date.start if self.date else None
    
    @property
    def end_date(self) -> Optional[datetime]:
        """Get end date."""
        return self.date.end if self.date else None
    
    def to_notion_format(self) -> Dict[str, Any]:
        if self.date:
            date_data = {"start": self.date.start.isoformat()}
            if self.date.end:
                date_data["end"] = self.date.end.isoformat()
            if self.date.time_zone:
                date_data["time_zone"] = self.date.time_zone
            return {"date": date_data}
        return {"date": None}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionDate":
        date_data = data.get("date")
        if date_data:
            start = datetime.fromisoformat(date_data["start"])
            end = datetime.fromisoformat(date_data["end"]) if date_data.get("end") else None
            date_range = NotionDateRange(
                start=start,
                end=end,
                time_zone=date_data.get("time_zone")
            )
        else:
            date_range = None
        return cls(date=date_range)


# People property

class Person(BaseModel):
    """Notion person object."""
    object: Literal["user"] = "user"
    id: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    type: Optional[str] = None
    person: Optional[Dict[str, Any]] = None


class NotionPeople(NotionProperty):
    """Notion people property."""
    
    people: List[Person] = Field(default_factory=list)
    
    def __init__(self, people: Optional[List[Union[str, Person]]] = None, **kwargs):
        if people:
            people_list = []
            for person in people:
                if isinstance(person, str):
                    people_list.append(Person(id=person))
                else:
                    people_list.append(person)
        else:
            people_list = kwargs.get("people", [])
            
        super().__init__(people=people_list, **kwargs)
    
    @property
    def user_ids(self) -> List[str]:
        """Get user IDs."""
        return [person.id for person in self.people]
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {"people": [{"id": person.id} for person in self.people]}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionPeople":
        people_data = data.get("people", [])
        people = [Person(**person) for person in people_data]
        return cls(people=people)


# Other basic properties

class NotionCheckbox(NotionProperty):
    """Notion checkbox property."""
    
    checkbox: bool = False
    
    def __init__(self, value: bool = False, **kwargs):
        super().__init__(checkbox=value, **kwargs)
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {"checkbox": self.checkbox}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionCheckbox":
        return cls(checkbox=data.get("checkbox", False))


class NotionURL(NotionProperty):
    """Notion URL property."""
    
    url: Optional[str] = None
    
    def __init__(self, url: Optional[str] = None, **kwargs):
        super().__init__(url=url, **kwargs)
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {"url": self.url}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionURL":
        return cls(url=data.get("url"))


class NotionEmail(NotionProperty):
    """Notion email property."""
    
    email: Optional[str] = None
    
    def __init__(self, email: Optional[str] = None, **kwargs):
        super().__init__(email=email, **kwargs)
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {"email": self.email}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionEmail":
        return cls(email=data.get("email"))


class NotionPhoneNumber(NotionProperty):
    """Notion phone number property."""
    
    phone_number: Optional[str] = None
    
    def __init__(self, phone: Optional[str] = None, **kwargs):
        super().__init__(phone_number=phone, **kwargs)
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {"phone_number": self.phone_number}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionPhoneNumber":
        return cls(phone_number=data.get("phone_number"))


# File property

class FileObject(BaseModel):
    """Notion file object."""
    name: str
    type: Literal["external", "file"] = "external"
    external: Optional[Dict[str, str]] = None
    file: Optional[Dict[str, str]] = None


class NotionFiles(NotionProperty):
    """Notion files property."""
    
    files: List[FileObject] = Field(default_factory=list)
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {"files": [f.dict() for f in self.files]}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionFiles":
        files_data = data.get("files", [])
        files = [FileObject(**f) for f in files_data]
        return cls(files=files)


# Formula property (read-only)

class NotionFormula(NotionProperty):
    """Notion formula property (read-only)."""
    
    formula: Dict[str, Any] = Field(default_factory=dict)
    
    def to_notion_format(self) -> Dict[str, Any]:
        # Formulas are read-only
        return {}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionFormula":
        return cls(formula=data.get("formula", {}))


# Relation property

RelationType = TypeVar("RelationType", bound=str)

class NotionRelation(NotionProperty, Generic[RelationType]):
    """Notion relation property."""
    
    relation: List[Dict[str, str]] = Field(default_factory=list)
    
    def __init__(self, page_ids: Optional[List[str]] = None, **kwargs):
        if page_ids:
            relation = [{"id": page_id} for page_id in page_ids]
        else:
            relation = kwargs.get("relation", [])
            
        super().__init__(relation=relation, **kwargs)
    
    @property
    def page_ids(self) -> List[str]:
        """Get related page IDs."""
        return [rel["id"] for rel in self.relation]
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {"relation": self.relation}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionRelation":
        relation_data = data.get("relation", [])
        return cls(relation=relation_data)


# Rollup property (read-only)

class NotionRollup(NotionProperty):
    """Notion rollup property (read-only)."""
    
    rollup: Dict[str, Any] = Field(default_factory=dict)
    
    def to_notion_format(self) -> Dict[str, Any]:
        # Rollups are read-only
        return {}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionRollup":
        return cls(rollup=data.get("rollup", {}))


# System properties (read-only)

class NotionCreatedTime(NotionProperty):
    """Notion created time property (read-only)."""
    
    created_time: Optional[datetime] = None
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionCreatedTime":
        created_time_str = data.get("created_time")
        created_time = datetime.fromisoformat(created_time_str) if created_time_str else None
        return cls(created_time=created_time)


class NotionCreatedBy(NotionProperty):
    """Notion created by property (read-only)."""
    
    created_by: Optional[Person] = None
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionCreatedBy":
        created_by_data = data.get("created_by")
        created_by = Person(**created_by_data) if created_by_data else None
        return cls(created_by=created_by)


class NotionLastEditedTime(NotionProperty):
    """Notion last edited time property (read-only)."""
    
    last_edited_time: Optional[datetime] = None
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionLastEditedTime":
        last_edited_time_str = data.get("last_edited_time")
        last_edited_time = datetime.fromisoformat(last_edited_time_str) if last_edited_time_str else None
        return cls(last_edited_time=last_edited_time)


class NotionLastEditedBy(NotionProperty):
    """Notion last edited by property (read-only)."""
    
    last_edited_by: Optional[Person] = None
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionLastEditedBy":
        last_edited_by_data = data.get("last_edited_by")
        last_edited_by = Person(**last_edited_by_data) if last_edited_by_data else None
        return cls(last_edited_by=last_edited_by)


# Status property (newer Notion feature)

class StatusOption(BaseModel):
    """Notion status option."""
    id: str
    name: str
    color: str


class NotionStatus(NotionProperty):
    """Notion status property."""
    
    status: Optional[StatusOption] = None
    
    def __init__(self, value: Optional[Union[str, StatusOption]] = None, **kwargs):
        if isinstance(value, str):
            status = StatusOption(id="", name=value, color="default")
        elif isinstance(value, StatusOption):
            status = value
        else:
            status = kwargs.get("status")
            
        super().__init__(status=status, **kwargs)
    
    @property
    def value(self) -> Optional[str]:
        """Get the status value."""
        return self.status.name if self.status else None
    
    def to_notion_format(self) -> Dict[str, Any]:
        if self.status:
            return {"status": {"name": self.status.name}}
        return {"status": None}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionStatus":
        status_data = data.get("status")
        if status_data:
            status = StatusOption(**status_data)
        else:
            status = None
        return cls(status=status)


# Unique ID property (read-only)

class NotionUniqueID(NotionProperty):
    """Notion unique ID property (read-only)."""
    
    unique_id: Optional[Dict[str, Any]] = None
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {}
    
    @classmethod
    def from_notion_format(cls, data: Dict[str, Any]) -> "NotionUniqueID":
        return cls(unique_id=data.get("unique_id"))


# Export all property types
__all__ = [
    "FileObject",
    "NotionCheckbox",
    "NotionCreatedBy",
    "NotionCreatedTime",
    "NotionDate",
    "NotionDateRange",
    "NotionEmail",
    "NotionFiles",
    "NotionFormula",
    "NotionLastEditedBy",
    "NotionLastEditedTime",
    "NotionMultiSelect",
    "NotionNumber",
    "NotionPeople",
    "NotionPhoneNumber",
    "NotionProperty",
    "NotionRelation",
    "NotionRollup",
    "NotionSelect",
    "NotionStatus",
    "NotionText",
    "NotionTitle",
    "NotionURL",
    "NotionUniqueID",
    "Person",
    "RichTextObject",
    "SelectOption",
    "StatusOption",
]
