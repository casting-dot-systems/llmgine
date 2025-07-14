# POST /api/engines
# - Create a new engine instance
# - Body: Engine configuration (type, model, parameters)

# GET /api/engines
# - List all active engines

# GET /api/engines/{engine_id}
# - Get engine details and status

# DELETE /api/engines/{engine_id}
# - Stop and cleanup an engine

# POST /api/engines/{engine_id}/execute
# - Execute a prompt/command on specific engine