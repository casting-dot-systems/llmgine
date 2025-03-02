"""
Command and event handler implementations for the LLMgine messaging system.

This module demonstrates how to implement and register command handlers
and event subscribers with the message bus.
"""

import logging
from typing import Dict, Any, Optional

from .bus import message_bus
from .commands import (
    CreateResourceCommand,
    UpdateResourceCommand,
    DeleteResourceCommand,
)
from .events import (
    ResourceCreatedEvent,
    ResourceUpdatedEvent,
    ResourceDeletedEvent,
    SystemEvent,
)


logger = logging.getLogger(__name__)


# Command Handlers
def handle_create_resource(command: CreateResourceCommand) -> str:
    """Handle the CreateResource command.
    
    Args:
        command: The command to handle
        
    Returns:
        The ID of the created resource
    """
    logger.info(f"Creating resource of type {command.resource_type}")
    
    # Generate a resource ID (in a real system, this would come from the repository)
    resource_id = f"res_{command.resource_type}_{command.command_id[:8]}"
    
    # In a real system, you would persist the resource here
    # Example: repository.add(Resource(id=resource_id, type=command.resource_type, data=command.resource_data))
    
    # Create and emit domain event
    event = ResourceCreatedEvent(
        resource_id=resource_id,
        resource_type=command.resource_type,
        resource_data=command.resource_data
    )
    
    # Add the event to be emitted after command handling
    message_bus.add_pending_event(event)
    
    return resource_id


def handle_update_resource(command: UpdateResourceCommand) -> bool:
    """Handle the UpdateResource command.
    
    Args:
        command: The command to handle
        
    Returns:
        True if the resource was updated successfully
    """
    logger.info(f"Updating resource {command.resource_id} of type {command.resource_type}")
    
    # In a real system, you would update the resource here
    # Example: 
    # resource = repository.get(command.resource_id)
    # if not resource:
    #     raise ResourceNotFound(command.resource_id)
    # previous_data = resource.data.copy()
    # resource.update(command.resource_data)
    
    # Create and emit domain event
    event = ResourceUpdatedEvent(
        resource_id=command.resource_id,
        resource_type=command.resource_type,
        resource_data=command.resource_data,
        # previous_data=previous_data  # In a real system, this would be the actual previous data
    )
    
    # Add the event to be emitted after command handling
    message_bus.add_pending_event(event)
    
    return True


def handle_delete_resource(command: DeleteResourceCommand) -> bool:
    """Handle the DeleteResource command.
    
    Args:
        command: The command to handle
        
    Returns:
        True if the resource was deleted successfully
    """
    logger.info(f"Deleting resource {command.resource_id} of type {command.resource_type}")
    
    # In a real system, you would delete the resource here
    # Example: 
    # resource = repository.get(command.resource_id)
    # if not resource:
    #     raise ResourceNotFound(command.resource_id)
    # repository.remove(command.resource_id)
    
    # Create and emit domain event
    event = ResourceDeletedEvent(
        resource_id=command.resource_id,
        resource_type=command.resource_type,
    )
    
    # Add the event to be emitted after command handling
    message_bus.add_pending_event(event)
    
    return True


# Event Subscribers
def log_resource_event(event: ResourceCreatedEvent):
    """Log resource creation events."""
    logger.info(f"Resource event logged: {event.event_type} for {event.resource_id}")


def notify_resource_created(event: ResourceCreatedEvent):
    """Send notifications when resources are created."""
    logger.info(f"Resource created notification: {event.resource_id} of type {event.resource_type}")
    # In a real system, you would send notifications here
    # Example: notification_service.send(f"Resource {event.resource_id} created")


def update_resource_cache(event: ResourceUpdatedEvent):
    """Update caches when resources are updated."""
    logger.info(f"Updating cache for resource: {event.resource_id}")
    # In a real system, you would update caches here
    # Example: cache_service.update(event.resource_id, event.resource_data)


def handle_system_event(event: SystemEvent):
    """React to system events."""
    if event.severity in ("error", "critical"):
        logger.error(f"System {event.severity} in {event.component}: {event.message}")
        # Example: alert_service.send_alert(event.severity, event.component, event.message)
    else:
        logger.info(f"System {event.severity} in {event.component}: {event.message}")


def register_handlers():
    """Register all command handlers and event subscribers with the message bus."""
    # Register command handlers
    message_bus.register_command(CreateResourceCommand, handle_create_resource)
    message_bus.register_command(UpdateResourceCommand, handle_update_resource)
    message_bus.register_command(DeleteResourceCommand, handle_delete_resource)
    
    # Register event subscribers
    message_bus.subscribe_event("resource.created", log_resource_event)
    message_bus.subscribe_event("resource.created", notify_resource_created)
    message_bus.subscribe_event("resource.updated", log_resource_event)
    message_bus.subscribe_event("resource.updated", update_resource_cache)
    message_bus.subscribe_event("resource.deleted", log_resource_event)
    message_bus.subscribe_event("system.*.error", handle_system_event)
    message_bus.subscribe_event("system.*.critical", handle_system_event)
    
    logger.info("All message handlers registered") 