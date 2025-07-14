# POST /api/sessions/{session_id}/commands
# - Execute a command on the message bus
# - Body: Command data (command_type, parameters, metadata)

# GET /api/sessions/{session_id}/commands/{command_id}
# - Get command execution status and result

# POST /api/sessions/{session_id}/commands/batch
# - Execute multiple commands in sequence