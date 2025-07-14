"""Type-safe sort builders for Notion database queries."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class SortCondition(BaseModel):
    """Represents a sort condition."""
    
    property: Optional[str] = None
    timestamp: Optional[str] = None
    direction: Literal["ascending", "descending"] = "ascending"
    
    def to_notion_format(self) -> Dict[str, Any]:
        """Convert to Notion API sort format."""
        result = {"direction": self.direction}
        
        if self.property:
            result["property"] = self.property
        elif self.timestamp:
            result["timestamp"] = self.timestamp
            
        return result


class PropertySortBuilder:
    """Builder for property-specific sorts."""
    
    def __init__(self, property_name: str):
        self.property_name = property_name
    
    def ascending(self) -> SortCondition:
        """Sort property in ascending order."""
        return SortCondition(
            property=self.property_name,
            direction="ascending"
        )
    
    def descending(self) -> SortCondition:
        """Sort property in descending order."""
        return SortCondition(
            property=self.property_name,
            direction="descending"
        )
    
    def asc(self) -> SortCondition:
        """Sort property in ascending order (shorthand)."""
        return self.ascending()
    
    def desc(self) -> SortCondition:
        """Sort property in descending order (shorthand)."""
        return self.descending()


class TimestampSortBuilder:
    """Builder for timestamp sorts."""
    
    def __init__(self, timestamp_type: str):
        self.timestamp_type = timestamp_type
    
    def ascending(self) -> SortCondition:
        """Sort timestamp in ascending order."""
        return SortCondition(
            timestamp=self.timestamp_type,
            direction="ascending"
        )
    
    def descending(self) -> SortCondition:
        """Sort timestamp in descending order."""
        return SortCondition(
            timestamp=self.timestamp_type,
            direction="descending"
        )
    
    def asc(self) -> SortCondition:
        """Sort timestamp in ascending order (shorthand)."""
        return self.ascending()
    
    def desc(self) -> SortCondition:
        """Sort timestamp in descending order (shorthand)."""
        return self.descending()


class SortBuilder:
    """Main sort builder for constructing Notion database queries."""
    
    def property(self, property_name: str) -> PropertySortBuilder:
        """Start building a property sort."""
        return PropertySortBuilder(property_name)
    
    def created_time(self) -> TimestampSortBuilder:
        """Sort by created time."""
        return TimestampSortBuilder("created_time")
    
    def last_edited_time(self) -> TimestampSortBuilder:
        """Sort by last edited time."""
        return TimestampSortBuilder("last_edited_time")
    
    @staticmethod
    def build(*conditions: SortCondition) -> List[Dict[str, Any]]:
        """Build final sort list for Notion API."""
        return [condition.to_notion_format() for condition in conditions]
    
    @staticmethod
    def quick_sort(
        property_name: str,
        direction: Literal["asc", "desc", "ascending", "descending"] = "asc"
    ) -> List[Dict[str, Any]]:
        """Quick sort helper for single property."""
        # Normalize direction
        if direction in ["asc", "ascending"]:
            dir_str = "ascending"
        else:
            dir_str = "descending"
            
        sort_condition = SortCondition(
            property=property_name,
            direction=dir_str
        )
        return [sort_condition.to_notion_format()]
    
    @staticmethod
    def quick_timestamp_sort(
        timestamp_type: Literal["created_time", "last_edited_time"],
        direction: Literal["asc", "desc", "ascending", "descending"] = "desc"
    ) -> List[Dict[str, Any]]:
        """Quick sort helper for timestamp properties."""
        # Normalize direction
        if direction in ["asc", "ascending"]:
            dir_str = "ascending"
        else:
            dir_str = "descending"
            
        sort_condition = SortCondition(
            timestamp=timestamp_type,
            direction=dir_str
        )
        return [sort_condition.to_notion_format()]


# Convenience functions for common sorting patterns

def sort_by_title_asc() -> List[Dict[str, Any]]:
    """Sort by title ascending."""
    return SortBuilder.quick_sort("title", "asc")


def sort_by_title_desc() -> List[Dict[str, Any]]:
    """Sort by title descending."""
    return SortBuilder.quick_sort("title", "desc")


def sort_by_created_time_newest() -> List[Dict[str, Any]]:
    """Sort by created time, newest first."""
    return SortBuilder.quick_timestamp_sort("created_time", "desc")


def sort_by_created_time_oldest() -> List[Dict[str, Any]]:
    """Sort by created time, oldest first."""
    return SortBuilder.quick_timestamp_sort("created_time", "asc")


def sort_by_last_edited_newest() -> List[Dict[str, Any]]:
    """Sort by last edited time, newest first."""
    return SortBuilder.quick_timestamp_sort("last_edited_time", "desc")


def sort_by_last_edited_oldest() -> List[Dict[str, Any]]:
    """Sort by last edited time, oldest first."""
    return SortBuilder.quick_timestamp_sort("last_edited_time", "asc")


def multi_sort(*sorts: SortCondition) -> List[Dict[str, Any]]:
    """Create multi-level sort."""
    return SortBuilder.build(*sorts)
