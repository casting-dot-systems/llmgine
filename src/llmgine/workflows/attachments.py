from typing import Any, Type, TYPE_CHECKING, List, Tuple, Optional

if TYPE_CHECKING:
    from llmgine.workflows.blocks import Block


class Slot:
    def __init__(self, name: str, type: Type, block: 'Block'):
        self.id = id(self)
        self.name = name
        self.type = type
        self.block = block
        self.data = None
        self.connected_head = None
    
    def receive_data(self, data: Any):
        # Skip validation if data is None (for reset operations)
        if data is not None and not isinstance(data, self.type):
            raise TypeError(f"Type mismatch for slot '{self.name}': Expected {self.type}, got {type(data)}")
        self.data = data
        
        # Notify the block that data was received
        if hasattr(self.block, 'check_and_compile_payload'):
            self.block.check_and_compile_payload()


class Head:
    def __init__(self, name: str, type: Type, block: 'Block'):
        self.id = id(self)
        self.name = name
        self.type = type
        self.block = block
        self.data = None
        self.connected_slot = None
        self.connected_slots: List[Tuple[int, str]] = []

    def connect(self, slot: Slot):
        """Connect this head to a slot"""
        if not issubclass(self.type, slot.type):
            raise TypeError(f"Type mismatch: Head '{self.name}' of type {self.type} cannot connect to slot '{slot.name}' of type {slot.type}")

        self.connected_slot = slot
        slot.connected_head = self
        
        # Store connection info in the list format as well
        if hasattr(slot, 'block') and hasattr(slot.block, 'id'):
            self.connected_slots = [(slot.block.id, slot.name)]

    def send_data(self, data: Any):
        """Send data to the connected slot"""
        # Skip validation if data is None (for reset operations)
        if data is not None and not isinstance(data, self.type):
            raise TypeError(f"Type mismatch for head '{self.name}': Expected {self.type}, got {type(data)}")
        
        self.data = data
        
        if self.connected_slot:
            # Queue the target block for execution
            if hasattr(self.connected_slot.block, 'workflow') and self.connected_slot.block.workflow:
                self.connected_slot.block.workflow.queue_block(self.connected_slot.block)
            
            # Pass data to the connected slot
            self.connected_slot.receive_data(data)

