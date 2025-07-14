# POST /api/sessions/{session_id}/handlers/commands
# - Register a command handler
# - Body: Command type and handler function

# POST /api/sessions/{session_id}/handlers/events
# - Register an event handler
# - Body: Event type and handler function

# DELETE /api/sessions/{session_id}/handlers/commands/{command_type}
# - Unregister a command handler

# DELETE /api/sessions/{session_id}/handlers/events/{event_type}
# - Unregister an event handler