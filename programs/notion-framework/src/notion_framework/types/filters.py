"""Type-safe filter builders for Notion database queries."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class FilterCondition(BaseModel, ABC):
    """Base class for filter conditions."""
    
    @abstractmethod
    def to_notion_format(self) -> Dict[str, Any]:
        """Convert to Notion API filter format."""
        pass


class PropertyFilter(FilterCondition):
    """Filter for a specific property."""
    
    property_name: str
    property_type: str
    condition: Dict[str, Any]
    
    def __init__(self, property_name: str, property_type: str, condition: Dict[str, Any]):
        super().__init__(
            property_name=property_name,
            property_type=property_type,
            condition=condition
        )
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {
            "property": self.property_name,
            self.property_type: self.condition
        }


class CompoundFilter(FilterCondition):
    """Compound filter with AND/OR logic."""
    
    operator: str
    conditions: List[FilterCondition]
    
    def __init__(self, operator: str, conditions: List[FilterCondition]):
        super().__init__(operator=operator, conditions=conditions)
    
    def to_notion_format(self) -> Dict[str, Any]:
        return {
            self.operator: [condition.to_notion_format() for condition in self.conditions]
        }


class PropertyFilterBuilder:
    """Builder for property-specific filters."""
    
    def __init__(self, property_name: str):
        self.property_name = property_name
    
    # Text property filters
    def text(self) -> "TextFilterBuilder":
        """Build text property filters."""
        return TextFilterBuilder(self.property_name)
    
    def title(self) -> "TextFilterBuilder":
        """Build title property filters."""
        return TextFilterBuilder(self.property_name, property_type="title")
    
    def rich_text(self) -> "TextFilterBuilder":
        """Build rich text property filters."""
        return TextFilterBuilder(self.property_name, property_type="rich_text")
    
    # Number property filters
    def number(self) -> "NumberFilterBuilder":
        """Build number property filters."""
        return NumberFilterBuilder(self.property_name)
    
    # Select property filters
    def select(self) -> "SelectFilterBuilder":
        """Build select property filters."""
        return SelectFilterBuilder(self.property_name)
    
    def multi_select(self) -> "MultiSelectFilterBuilder":
        """Build multi-select property filters."""
        return MultiSelectFilterBuilder(self.property_name)
    
    # Date property filters
    def date(self) -> "DateFilterBuilder":
        """Build date property filters."""
        return DateFilterBuilder(self.property_name)
    
    # People property filters
    def people(self) -> "PeopleFilterBuilder":
        """Build people property filters."""
        return PeopleFilterBuilder(self.property_name)
    
    # Checkbox property filters
    def checkbox(self) -> "CheckboxFilterBuilder":
        """Build checkbox property filters."""
        return CheckboxFilterBuilder(self.property_name)
    
    # URL property filters
    def url(self) -> "TextFilterBuilder":
        """Build URL property filters."""
        return TextFilterBuilder(self.property_name, property_type="url")
    
    # Email property filters
    def email(self) -> "TextFilterBuilder":
        """Build email property filters."""
        return TextFilterBuilder(self.property_name, property_type="email")
    
    # Phone number property filters
    def phone_number(self) -> "TextFilterBuilder":
        """Build phone number property filters."""
        return TextFilterBuilder(self.property_name, property_type="phone_number")
    
    # Relation property filters
    def relation(self) -> "RelationFilterBuilder":
        """Build relation property filters."""
        return RelationFilterBuilder(self.property_name)
    
    # Formula property filters
    def formula(self) -> "FormulaFilterBuilder":
        """Build formula property filters."""
        return FormulaFilterBuilder(self.property_name)
    
    # Created/edited time filters
    def created_time(self) -> "DateFilterBuilder":
        """Build created time property filters."""
        return DateFilterBuilder(self.property_name, property_type="created_time")
    
    def last_edited_time(self) -> "DateFilterBuilder":
        """Build last edited time property filters."""
        return DateFilterBuilder(self.property_name, property_type="last_edited_time")
    
    # Created/edited by filters
    def created_by(self) -> "PeopleFilterBuilder":
        """Build created by property filters."""
        return PeopleFilterBuilder(self.property_name, property_type="created_by")
    
    def last_edited_by(self) -> "PeopleFilterBuilder":
        """Build last edited by property filters."""
        return PeopleFilterBuilder(self.property_name, property_type="last_edited_by")


class TextFilterBuilder:
    """Builder for text-based property filters."""
    
    def __init__(self, property_name: str, property_type: str = "rich_text"):
        self.property_name = property_name
        self.property_type = property_type
    
    def equals(self, value: str) -> PropertyFilter:
        """Text equals filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"equals": value}
        )
    
    def does_not_equal(self, value: str) -> PropertyFilter:
        """Text does not equal filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"does_not_equal": value}
        )
    
    def contains(self, value: str) -> PropertyFilter:
        """Text contains filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"contains": value}
        )
    
    def does_not_contain(self, value: str) -> PropertyFilter:
        """Text does not contain filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"does_not_contain": value}
        )
    
    def starts_with(self, value: str) -> PropertyFilter:
        """Text starts with filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"starts_with": value}
        )
    
    def ends_with(self, value: str) -> PropertyFilter:
        """Text ends with filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"ends_with": value}
        )
    
    def is_empty(self) -> PropertyFilter:
        """Text is empty filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"is_empty": True}
        )
    
    def is_not_empty(self) -> PropertyFilter:
        """Text is not empty filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"is_not_empty": True}
        )


class NumberFilterBuilder:
    """Builder for number property filters."""
    
    def __init__(self, property_name: str):
        self.property_name = property_name
    
    def equals(self, value: Union[int, float]) -> PropertyFilter:
        """Number equals filter."""
        return PropertyFilter(
            self.property_name,
            "number",
            {"equals": value}
        )
    
    def does_not_equal(self, value: Union[int, float]) -> PropertyFilter:
        """Number does not equal filter."""
        return PropertyFilter(
            self.property_name,
            "number",
            {"does_not_equal": value}
        )
    
    def greater_than(self, value: Union[int, float]) -> PropertyFilter:
        """Number greater than filter."""
        return PropertyFilter(
            self.property_name,
            "number",
            {"greater_than": value}
        )
    
    def less_than(self, value: Union[int, float]) -> PropertyFilter:
        """Number less than filter."""
        return PropertyFilter(
            self.property_name,
            "number",
            {"less_than": value}
        )
    
    def greater_than_or_equal_to(self, value: Union[int, float]) -> PropertyFilter:
        """Number greater than or equal to filter."""
        return PropertyFilter(
            self.property_name,
            "number",
            {"greater_than_or_equal_to": value}
        )
    
    def less_than_or_equal_to(self, value: Union[int, float]) -> PropertyFilter:
        """Number less than or equal to filter."""
        return PropertyFilter(
            self.property_name,
            "number",
            {"less_than_or_equal_to": value}
        )
    
    def is_empty(self) -> PropertyFilter:
        """Number is empty filter."""
        return PropertyFilter(
            self.property_name,
            "number",
            {"is_empty": True}
        )
    
    def is_not_empty(self) -> PropertyFilter:
        """Number is not empty filter."""
        return PropertyFilter(
            self.property_name,
            "number",
            {"is_not_empty": True}
        )


class SelectFilterBuilder:
    """Builder for select property filters."""
    
    def __init__(self, property_name: str):
        self.property_name = property_name
    
    def equals(self, value: str) -> PropertyFilter:
        """Select equals filter."""
        return PropertyFilter(
            self.property_name,
            "select",
            {"equals": value}
        )
    
    def does_not_equal(self, value: str) -> PropertyFilter:
        """Select does not equal filter."""
        return PropertyFilter(
            self.property_name,
            "select",
            {"does_not_equal": value}
        )
    
    def is_empty(self) -> PropertyFilter:
        """Select is empty filter."""
        return PropertyFilter(
            self.property_name,
            "select",
            {"is_empty": True}
        )
    
    def is_not_empty(self) -> PropertyFilter:
        """Select is not empty filter."""
        return PropertyFilter(
            self.property_name,
            "select",
            {"is_not_empty": True}
        )


class MultiSelectFilterBuilder:
    """Builder for multi-select property filters."""
    
    def __init__(self, property_name: str):
        self.property_name = property_name
    
    def contains(self, value: str) -> PropertyFilter:
        """Multi-select contains filter."""
        return PropertyFilter(
            self.property_name,
            "multi_select",
            {"contains": value}
        )
    
    def does_not_contain(self, value: str) -> PropertyFilter:
        """Multi-select does not contain filter."""
        return PropertyFilter(
            self.property_name,
            "multi_select",
            {"does_not_contain": value}
        )
    
    def is_empty(self) -> PropertyFilter:
        """Multi-select is empty filter."""
        return PropertyFilter(
            self.property_name,
            "multi_select",
            {"is_empty": True}
        )
    
    def is_not_empty(self) -> PropertyFilter:
        """Multi-select is not empty filter."""
        return PropertyFilter(
            self.property_name,
            "multi_select",
            {"is_not_empty": True}
        )


class DateFilterBuilder:
    """Builder for date property filters."""
    
    def __init__(self, property_name: str, property_type: str = "date"):
        self.property_name = property_name
        self.property_type = property_type
    
    def equals(self, date: Union[str, datetime]) -> PropertyFilter:
        """Date equals filter."""
        if isinstance(date, datetime):
            date = date.isoformat()
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"equals": date}
        )
    
    def before(self, date: Union[str, datetime]) -> PropertyFilter:
        """Date before filter."""
        if isinstance(date, datetime):
            date = date.isoformat()
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"before": date}
        )
    
    def after(self, date: Union[str, datetime]) -> PropertyFilter:
        """Date after filter."""
        if isinstance(date, datetime):
            date = date.isoformat()
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"after": date}
        )
    
    def on_or_before(self, date: Union[str, datetime]) -> PropertyFilter:
        """Date on or before filter."""
        if isinstance(date, datetime):
            date = date.isoformat()
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"on_or_before": date}
        )
    
    def on_or_after(self, date: Union[str, datetime]) -> PropertyFilter:
        """Date on or after filter."""
        if isinstance(date, datetime):
            date = date.isoformat()
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"on_or_after": date}
        )
    
    def past_week(self) -> PropertyFilter:
        """Date in past week filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"past_week": {}}
        )
    
    def past_month(self) -> PropertyFilter:
        """Date in past month filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"past_month": {}}
        )
    
    def past_year(self) -> PropertyFilter:
        """Date in past year filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"past_year": {}}
        )
    
    def next_week(self) -> PropertyFilter:
        """Date in next week filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"next_week": {}}
        )
    
    def next_month(self) -> PropertyFilter:
        """Date in next month filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"next_month": {}}
        )
    
    def next_year(self) -> PropertyFilter:
        """Date in next year filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"next_year": {}}
        )
    
    def is_empty(self) -> PropertyFilter:
        """Date is empty filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"is_empty": True}
        )
    
    def is_not_empty(self) -> PropertyFilter:
        """Date is not empty filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"is_not_empty": True}
        )


class PeopleFilterBuilder:
    """Builder for people property filters."""
    
    def __init__(self, property_name: str, property_type: str = "people"):
        self.property_name = property_name
        self.property_type = property_type
    
    def contains(self, user_id: str) -> PropertyFilter:
        """People contains filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"contains": user_id}
        )
    
    def does_not_contain(self, user_id: str) -> PropertyFilter:
        """People does not contain filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"does_not_contain": user_id}
        )
    
    def is_empty(self) -> PropertyFilter:
        """People is empty filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"is_empty": True}
        )
    
    def is_not_empty(self) -> PropertyFilter:
        """People is not empty filter."""
        return PropertyFilter(
            self.property_name,
            self.property_type,
            {"is_not_empty": True}
        )


class CheckboxFilterBuilder:
    """Builder for checkbox property filters."""
    
    def __init__(self, property_name: str):
        self.property_name = property_name
    
    def equals(self, value: bool) -> PropertyFilter:
        """Checkbox equals filter."""
        return PropertyFilter(
            self.property_name,
            "checkbox",
            {"equals": value}
        )
    
    def does_not_equal(self, value: bool) -> PropertyFilter:
        """Checkbox does not equal filter."""
        return PropertyFilter(
            self.property_name,
            "checkbox",
            {"does_not_equal": value}
        )


class RelationFilterBuilder:
    """Builder for relation property filters."""
    
    def __init__(self, property_name: str):
        self.property_name = property_name
    
    def contains(self, page_id: str) -> PropertyFilter:
        """Relation contains filter."""
        return PropertyFilter(
            self.property_name,
            "relation",
            {"contains": page_id}
        )
    
    def does_not_contain(self, page_id: str) -> PropertyFilter:
        """Relation does not contain filter."""
        return PropertyFilter(
            self.property_name,
            "relation",
            {"does_not_contain": page_id}
        )
    
    def is_empty(self) -> PropertyFilter:
        """Relation is empty filter."""
        return PropertyFilter(
            self.property_name,
            "relation",
            {"is_empty": True}
        )
    
    def is_not_empty(self) -> PropertyFilter:
        """Relation is not empty filter."""
        return PropertyFilter(
            self.property_name,
            "relation",
            {"is_not_empty": True}
        )


class FormulaFilterBuilder:
    """Builder for formula property filters."""
    
    def __init__(self, property_name: str):
        self.property_name = property_name
    
    def string(self) -> TextFilterBuilder:
        """Formula string filter."""
        return TextFilterBuilder(self.property_name, "formula")
    
    def number(self) -> NumberFilterBuilder:
        """Formula number filter."""
        return NumberFilterBuilder(self.property_name)
    
    def checkbox(self) -> CheckboxFilterBuilder:
        """Formula checkbox filter."""
        return CheckboxFilterBuilder(self.property_name)
    
    def date(self) -> DateFilterBuilder:
        """Formula date filter."""
        return DateFilterBuilder(self.property_name, "formula")


class FilterBuilder:
    """Main filter builder for constructing Notion database queries."""
    
    def property(self, property_name: str) -> PropertyFilterBuilder:
        """Start building a property filter."""
        return PropertyFilterBuilder(property_name)
    
    def and_(self, *conditions: FilterCondition) -> CompoundFilter:
        """Create an AND compound filter."""
        return CompoundFilter("and", list(conditions))
    
    def or_(self, *conditions: FilterCondition) -> CompoundFilter:
        """Create an OR compound filter."""
        return CompoundFilter("or", list(conditions))
    
    @staticmethod
    def combine_and(*conditions: FilterCondition) -> Optional[Dict[str, Any]]:
        """Combine conditions with AND logic."""
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0].to_notion_format()
        return CompoundFilter("and", list(conditions)).to_notion_format()
    
    @staticmethod
    def combine_or(*conditions: FilterCondition) -> Optional[Dict[str, Any]]:
        """Combine conditions with OR logic."""
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0].to_notion_format()
        return CompoundFilter("or", list(conditions)).to_notion_format()
