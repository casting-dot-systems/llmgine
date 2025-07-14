# POST /api/sessions/{session_id}/tools
# - Register a new tool
# - Body: Tool function and metadata

# GET /api/sessions/{session_id}/tools
# - List all registered tools for a session

# POST /api/sessions/{session_id}/tools/{tool_name}/execute
# - Execute a specific tool
# - Body: Tool arguments

# DELETE /api/sessions/{session_id}/tools/{tool_name}
# - Unregister a tool