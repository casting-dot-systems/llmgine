from typing import Any, Type

from llmgine.workflows.blocks import Block


class Slot:
    def __init__(self, name: str, type: Type, block: Block):
        self.id = id(self)
        self.name = name
        self.type = type
        self.block = block
        self.data = None
        self.connected_head = None
    
    def receive_data(self, data: Any):
        self.validate()
        self.data = data
        
    def validate(self):
        if not isinstance(self.data, self.type):
            raise ValueError(f"Type mismatch: Expected {self.type}, got {type(self.data)}")

class Head:
    def __init__(self, name: str, type: Type, block: Block):
        self.id = id(self)
        self.name = name
        self.type = type
        self.block = block
        self.data = None
        self.connected_slot = None

    def connect(self, slot: Slot):
        self.connected_slot = slot

    def send_data(self, data: Any):
        self.validate()
        self.data = data
        self.connected_slot.receive_data(data)
    
    def validate(self):
        if not isinstance(self.data, self.type):
            raise ValueError(f"Type mismatch: Expected {self.type}, got {type(self.data)}")

