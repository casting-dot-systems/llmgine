# POST /api/sessions/{session_id}/events
# - Publish an event to the message bus
# - Body: Event data (event_type, data, metadata)

# GET /api/sessions/{session_id}/events
# - Get events for a session (with filtering/pagination)

# GET /api/sessions/{session_id}/events/{event_id}
# - Get specific event details