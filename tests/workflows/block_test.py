# import pytest
# from enum import Enum
# from dataclasses import dataclass
# from typing import Tuple, Optional

# from llmgine.workflows.blocks import LogicBlock
# from llmgine.workflows.attachments import Socket, Router, Route
# from llmgine.workflows.exceptions import BlockExecutionError

# @dataclass
# class WeatherData:
#     temperature: float
#     conditions: str

# class WeatherAction(Enum):
#     STAY_INSIDE = "stay_inside"
#     GO_OUTSIDE = "go_outside"
#     SEEK_SHELTER = "seek_shelter"

# def test_logic_block_creation():
#     def weather_decision(data: WeatherData) -> Tuple[None, WeatherAction]:
#         if data.temperature > 30 or data.temperature < 0:
#             return None, WeatherAction.STAY_INSIDE
#         elif "storm" in data.conditions.lower():
#             return None, WeatherAction.SEEK_SHELTER
#         else:
#             return None, WeatherAction.GO_OUTSIDE

#     socket = Socket({"weather": WeatherData}, lambda x: x["weather"])
#     router = Router(WeatherAction)
    
#     block = LogicBlock(
#         function=weather_decision,
#         socket=socket,
#         router=router
#     )
    
#     assert block.function == weather_decision
#     assert block.socket == socket
#     assert block.router == router
#     assert block.socket.block == block
#     assert block.router.block == block

# def test_logic_block_execution():
#     def weather_decision(data: WeatherData) -> Tuple[None, WeatherAction]:
#         if data.temperature > 30:
#             return None, WeatherAction.STAY_INSIDE
#         return None, WeatherAction.GO_OUTSIDE

#     socket = Socket({"weather": WeatherData}, lambda x: x["weather"])
#     router = Router(WeatherAction)
    
#     block = LogicBlock(
#         function=weather_decision,
#         socket=socket,
#         router=router
#     )

#     # Test hot weather case
#     hot_weather = WeatherData(temperature=35, conditions="sunny")
#     socket.slots[0].recieve_data(hot_weather)
#     result = block.execute()
#     assert result[1] == WeatherAction.STAY_INSIDE

#     # Test nice weather case
#     nice_weather = WeatherData(temperature=25, conditions="sunny")
#     socket.slots[0].recieve_data(nice_weather)
#     result = block.execute()
#     assert result[1] == WeatherAction.GO_OUTSIDE

# def test_logic_block_validation():
#     def invalid_decision(data: WeatherData) -> WeatherAction:  # Wrong return type
#         return WeatherAction.STAY_INSIDE

#     socket = Socket({"weather": WeatherData}, lambda x: x["weather"])
#     router = Router(WeatherAction)
    
#     block = LogicBlock(
#         function=invalid_decision,
#         socket=socket,
#         router=router
#     )

#     with pytest.raises(BlockExecutionError):
#         block.validate()
