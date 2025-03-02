from llmgine.workflows import *
from tests.workflows.block_test import (
    WeatherModel,
    Action,
    get_weather,
    decide_action
)

# Create workflow
workflow = Workflow("weather_workflow", debug=True)

# Add start/end points
workflow.start.add_head("location", str)
workflow.start.add_head("time", int)
workflow.end.add_slot("activity", str)

# Create weather block
weather_block = ProcessBlock(
    function=get_weather,
    socket={
        "location": str,
        "time": int
    },
    plug={
        "weather": WeatherModel
    }
)

# Create action block
action_block = LogicBlock(
    function=decide_action,
    socket={
        "weather": WeatherModel
    },
    router=(Action, str)
)

# Connect blocks (automatically adds them to workflow)
weather_block.socket.slots["location"].attach(workflow.start.heads["location"])
weather_block.socket.slots["time"].attach(workflow.start.heads["time"])
action_block.socket.slots["weather"].attach(weather_block.plug.heads["weather"])

# Connect routes to end
for action in Action:
    action_block.router.add_route(action, workflow.end.slots["activity"])

# Execute workflow
result = workflow.execute({
    "location": "New York",
    "time": 1200
})

print(result.data)  # {"activity": "outdoor"}
print(result.metadata)  # Execution info
