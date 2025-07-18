"""Generated types for Notion databases."""

from typing import Literal, Union
from enum import Enum

class EventsProjectsID(str):
    """Type for Events/Projects database IDs."""
    pass

class MeetingsandTasksID(str):
    """Type for Meetings and Tasks database IDs."""
    pass

class TeamsID(str):
    """Type for Teams database IDs."""
    pass

class DocumentsID(str):
    """Type for Documents database IDs."""
    pass

class EventsProjects_Type(str, Enum):
    """Enum for Events/Projects Type property."""
    NOTE = "Note"
    EVENT = "Event"
    PROJECT = "Project"
    ADMIN = "Admin"
    PROGRAM = "Program"
    PORTFOLIO = "Portfolio"
    USER_STORY = "User Story"
    EPIC = "Epic"
    SPRINT = "Sprint"
    FEATURE = "Feature"

class EventsProjects_Progress(str, Enum):
    """Enum for Events/Projects Progress property."""
    ON_GOING = "On-Going"
    PROPOSAL = "Proposal"
    APPROVED = "Approved"
    PLANNING = "Planning"
    IN_PROGRESS = "In-Progress"
    FINISHED = "Finished"
    CANCELLED = "Cancelled"
    ARCHIVE = "Archive"
    PAUSED = "Paused"
    TO_REVIEW = "To-Review"
    COMPLETE = "Complete"

class EventsProjects_Priority(str, Enum):
    """Enum for Events/Projects Priority property."""
    _ = "⭐"
    __ = "⭐⭐"
    ___ = "⭐⭐⭐"
    ____ = "⭐⭐⭐⭐"
    _____ = "⭐⭐⭐⭐⭐"

class MeetingsandTasks_Priority(str, Enum):
    """Enum for Meetings and Tasks Priority property."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

