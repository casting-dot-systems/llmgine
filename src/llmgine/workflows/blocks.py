from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Optional, Tuple, Any, Dict, Type, List
from enum import Enum, auto
from abc import ABC, abstractmethod

from llmgine.messages.bus import MessageBus
from llmgine.workflows.attachments import Head, Slot
from ..observer.observability import imprint, LogEvent
from .exceptions import BlockExecutionError
from ..messages.events import Event
from llmgine.types.utils import Queue

if TYPE_CHECKING:
    from .workflow import Workflow

class BlockCreatedEvent(Event):
    """Event for when a block is created"""
    block: Block
    

class BlockStateChangedEvent(Event):
    """Event for when a block's state changes"""
    block: Block
    old_state: str
    new_state: str
    
class BlockExecutionStartedEvent(Event):
    """Event for when a block's execution starts"""
    block: Block
    
class BlockExecutionCompletedEvent(Event):
    """Event for when a block's execution completes"""
    block: Block
    
class BlockExecutionFailedEvent(Event):
    """Event for when a block's execution fails"""
    block: Block
    error: Exception
    
class BlockExecutionQueuedEvent(Event):
    """Event for when a block's execution is queued"""
    block: Block
    
class BlockExecutionRescheduledEvent(Event):
    """Event for when a block's execution is rescheduled"""
    block: Block

class BlockExecutionCompletedEvent(Event):
    """Event for when a block's execution completes"""
    block: Block
    
class BlockExecutionFailedEvent(Event):
    """Event for when a block's execution fails"""
    block: Block


class FunctionBlockStates(Enum):
    """States for a function block"""
    NEW = "NEW"
    AWAITING_INPUTS = "AWAITING_INPUTS"
    COMPILING = "COMPILING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    UNPACKING = "UNPACKING"
    SENDING_OUTPUTS = "SENDING_OUTPUTS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    

class Block:
    """Abstract base class for all blocks in a workflow"""
    pass

class WorkflowContext:
    """Base class for workflow context that can be extended with specific attributes"""
    def __init__(self, **kwargs):
        self._context: Dict[str, Any] = kwargs
        
    def get(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)
        
    def set(self, key: str, value: Any):
        self._context[key] = value
        
    def __getitem__(self, key: str) -> Any:
        return self._context[key]
        
    def __setitem__(self, key: str, value: Any):
        self._context[key] = value

class FunctionBlock(Block):
    def __init__(self, 
                 function: Callable,
                 input_schema: Dict[str, Type],
                 output_schema: Dict[str, Type],
                 queue: Queue,
                 compile_function: Optional[Callable] = None,
                 unpack_function: Optional[Callable] = None,
                 name: Optional[str] = None):
        """
        Initialize a function block with input and output schemas
        
        Args:
            function: The function to execute
            input_schema: Dictionary mapping slot names to expected types
            output_schema: Dictionary mapping head names to output types
            compile_function: Optional function to transform input data before execution
            unpack_function: Optional function to transform output data before sending
            name: Optional block name (defaults to function name)
        """
        self.id = id(self)
        self.name = name or function.__name__
        self.function = function
        self.compile_function = compile_function
        self.unpack_function = unpack_function
        self.log = []
        self.message_bus = MessageBus()
        self.state = FunctionBlockStates.NEW
        self.queue = queue

        # Create Socket with dictionary of slots
        self.socket = {
            key: Slot(
                name=key,
                type=type_val,
                block=self
            )
            for key, type_val in input_schema.items()
        }
        
        # Create Plug with dictionary of heads
        self.plug = {
            key: Head(
                name=key,
                type=type_val,
                block=self
            )
            for key, type_val in output_schema.items()
        }
        
        self.workflow = None

    def set_workflow(self, workflow: Workflow):
        self.workflow = workflow
    
    def raw_execute(self, function_parameters: Dict[str, Any]) -> Any:
        """
        Execute the process block's function and return the result
        Used for testing and debugging, as it doesn't receive data from socket or send data to plug
        """
        results = self.function(**function_parameters)
        if self.unpack_function:
            results = self.unpack_function(results)
        return results

    def execute(self) -> Any:
        """Execute the function block and pass result to connected blocks"""
        # Execute the function
        try:
            self.log_event(f"Block {self.name} executing with payload: {self.payload}", "block_executing")
            result = self.function(**self.payload)
            self.log_event(f"Block {self.name} executed with result: {result}", "block_executed")
            
            # Apply unpack function if provided before passing to connected blocks
            if self.unpack_function:
                output_data = self.unpack_function(result)
                self.log_event(f"Block {self.name} result {result} unpacked to: {output_data}", "block_unpacked")
            else:
                output_data = result
                
            # Store the result in heads and pass to connected slots
            self.pass_data_to_connected_slots(output_data)
                
            return result
            
        except Exception as e:
            self.log_event(f"Block {self.name} failed with error: {str(e)}", "block_failed")
            raise BlockExecutionError(f"Error executing process block: {str(e)}")

    def validate(self):
        """Validate the block's configuration"""
        # Check that all required input slots have valid types
        for name, slot in self.slots.items():
            if not isinstance(slot["type"], type):
                return False
        
        # Check that all output heads have valid types
        for name, head in self.heads.items():
            if not isinstance(head["type"], type):
                return False
                
        return True
    
    def receive_data(self, slot_name: str, data: Any) -> None:
        """
        Receive data into a specific slot
        
        Args:
            slot_name: Name of the slot to receive data
            data: Data to store in the slot
        """
        if slot_name not in self.slots:
            raise ValueError(f"Slot {slot_name} does not exist in block {self.name}")
            
        slot = self.slots[slot_name]
        
        # Type check
        if not isinstance(data, slot["type"]):
            raise TypeError(f"Type mismatch: Expected {slot['type']}, got {type(data)}")
            
        # Store the data
        slot["data"] = data
        self.log_event(f"Slot {slot_name} received data: {data}", "slot_received_data")
        
        # Check if we can compile a complete payload
        self.check_and_compile_payload()
    
    def check_and_compile_payload(self) -> None:
        """Check if all required slots have data and compile them into a payload"""
        # Check if all slots have data
        if not all(slot["data"] is not None for slot in self.slots.values()):
            self.incomplete_payload()
            return
            
        # Compile the payload
        if self.compile_function:
            # Custom compilation
            payload_data = {name: slot["data"] for name, slot in self.slots.items()}
            
            # Check if workflow_context is needed
            from inspect import signature
            sig = signature(self.compile_function)
            if "workflow_context" in sig.parameters:
                payload_data["workflow_context"] = self.workflow
                
            try:
                payload = self.compile_function(**payload_data)
            except Exception as e:
                self.log_event(f"Error compiling payload: {str(e)}", "compile_error")
                raise ValueError(f"Error compiling payload: {str(e)}")
        else:
            # Native compilation - just create a dictionary
            payload = {name: slot["data"] for name, slot in self.slots.items()}
            
        self.complete_payload(payload)
    
    def incomplete_payload(self) -> None:
        """Handle incomplete payload - requeue the block for later execution"""
        self.queue.requeue()
    
    def complete_payload(self, payload: Dict[str, Any]) -> None:
        """
        Set the payload and prepare for execution
        
        Args:
            payload: The compiled payload
        """
        self.payload = payload
        self.log_event(f"Block {self.name} received payload: {payload}", "block_received_payload")
        self.requeue()
    
    def pass_data_to_connected_slots(self, data: Any) -> None:
        """
        Pass data to connected slots in other blocks
        
        Args:
            data: Data to pass
        """
        for head_name, head in self.heads.items():
            # Store data in the head
            head["data"] = data
            
            # Pass to all connected slots
            for connected_slot in head["connected_slots"]:
                # Split block_id and slot_name
                block_id, slot_name = connected_slot
                
                # Find the block and pass the data
                for block in self.workflow.blocks:
                    if block.id == block_id:
                        block.receive_data(slot_name, data)
                        break
    
    def connect_head_to_slot(self, head_name: str, target_block: 'FunctionBlock', slot_name: str) -> None:
        """
        Connect a head to a slot in another block
        
        Args:
            head_name: Name of the head to connect
            target_block: Block to connect to
            slot_name: Name of the slot to connect to
        """
        if head_name not in self.heads:
            raise ValueError(f"Head {head_name} does not exist in block {self.name}")
            
        if slot_name not in target_block.slots:
            raise ValueError(f"Slot {slot_name} does not exist in block {target_block.name}")
            
        # Check type compatibility
        head_type = self.heads[head_name]["type"]
        slot_type = target_block.slots[slot_name]["type"]
        
        if not issubclass(head_type, slot_type):
            raise TypeError(f"Type mismatch: Head provides {head_type}, but slot expects {slot_type}")
        
        # Add the connection
        self.heads[head_name]["connected_slots"].append((target_block.id, slot_name))
        target_block.slots[slot_name]["connected_head"] = (self.id, head_name)
        
        self.log_event(
            f"Connected head {head_name} to slot {slot_name} in block {target_block.name}",
            "connection_established"
        )
    
    def requeue(self):
        """Requeue the block for execution"""
        if self.workflow:
            self.workflow.requeue_block(self)
    
    def reset(self):
        """Reset the block to its initial state"""
        # Reset all slots
        for slot in self.slots.values():
            slot["data"] = None
            
        # Reset all heads
        for head in self.heads.values():
            head["data"] = None
            
        self.payload = None
        self.log_event(f"Block {self.name} reset", "block_reset")

class LogicBlock(Block):
    def __init__(self, 
                 function: Callable,
                 input_schema: Dict[str, Type],
                 route_enum: Type[Enum],
                 compile_function: Optional[Callable] = None,
                 unpack_function: Optional[Callable] = None,
                 name: Optional[str] = None):
        """
        Initialize a logic block with input schema and routing enum
        
        Args:
            function: The function to execute
            input_schema: Dictionary mapping slot names to expected types
            route_enum: Enum type for routing decisions
            compile_function: Optional function to transform input data before execution
            unpack_function: Optional function to transform output data before routing
            name: Optional block name (defaults to function name)
        """
        self.id = id(self)
        self.name = name or function.__name__
        self.function = function
        self.compile_function = compile_function
        self.unpack_function = unpack_function
        
        # Replace Socket with dictionary of slots
        self.slots = {
            key: {"type": type_val, "data": None, "connected_head": None} 
            for key, type_val in input_schema.items()
        }
        
        # Store routes configuration
        self.route_enum = route_enum
        self.routes = {
            route: {"connected_block_id": None, "connected_slot": None}
            for route in route_enum
        }
        
        self.payload = None
        self.workflow = None

    def set_workflow(self, workflow: Workflow):
        self.workflow = workflow
    
    def log_event(self, message: str, event_type: str, metadata: Optional[Dict[str, Any]] = None):
        if metadata:
            metadata["block_id"] = self.id
        imprint.emit(LogEvent(
            message=message,
            event_type=event_type,
            metadata=metadata or {"block_id": self.id}
        ))

    def execute(self) -> Tuple[Any, Enum]:
        """Execute the logic block and route output to the appropriate block"""
        try:
            # Validate before execution
            self.validate()
            
            # Compile input data from slots
            if self.compile_function:
                input_data = self.compile_function({name: slot["data"] for name, slot in self.slots.items()})
            else:
                input_data = {name: slot["data"] for name, slot in self.slots.items()}
                
            self.log_event(f"Logic block {self.name} executing with data: {input_data}", "logic_block_executing")
            
            # Execute the function
            result = self.function(input_data)
            
            # Validate result is a tuple with (data, decision)
            if not isinstance(result, tuple) or len(result) != 2:
                raise BlockExecutionError("Logic block function must return a tuple of (data, decision)")
                
            data, decision = result
            
            # Validate decision is of the correct enum type
            if not isinstance(decision, self.route_enum):
                raise BlockExecutionError(f"Decision must be of type {self.route_enum}")
                
            self.log_event(f"Logic block {self.name} decided route: {decision}", "logic_block_decided")
            
            # Apply unpack function if provided
            if self.unpack_function and data is not None:
                data = self.unpack_function(data)
                
            # Trigger the route
            self.trigger_route(decision, data)
            
            return result
            
        except Exception as e:
            self.log_event(f"Logic block {self.name} failed with error: {str(e)}", "logic_block_failed")
            raise BlockExecutionError(f"Error executing logic block: {str(e)}")

    def validate(self):
        """Validate the logic block's configuration"""
        # Check that all required input slots have valid types
        for name, slot in self.slots.items():
            if not isinstance(slot["type"], type):
                return False
                
        # Check that all routes are connected
        for route, config in self.routes.items():
            if config["connected_block_id"] is None or config["connected_slot"] is None:
                raise BlockExecutionError(f"Route {route} is not connected to any block")
                
        return True
    
    def receive_data(self, slot_name: str, data: Any) -> None:
        """
        Receive data into a specific slot
        
        Args:
            slot_name: Name of the slot to receive data
            data: Data to store in the slot
        """
        if slot_name not in self.slots:
            raise ValueError(f"Slot {slot_name} does not exist in block {self.name}")
            
        slot = self.slots[slot_name]
        
        # Type check
        if not isinstance(data, slot["type"]):
            raise TypeError(f"Type mismatch: Expected {slot['type']}, got {type(data)}")
            
        # Store the data
        slot["data"] = data
        self.log_event(f"Slot {slot_name} received data: {data}", "slot_received_data")
        
        # Check if we can compile a complete payload
        self.check_and_compile_payload()
    
    def check_and_compile_payload(self) -> None:
        """Check if all required slots have data and compile them into a payload"""
        # Check if all slots have data
        if not all(slot["data"] is not None for slot in self.slots.values()):
            return
            
        # Requeue for execution
        self.requeue()
    
    def connect_route(self, route: Enum, target_block: Block, slot_name: str) -> None:
        """
        Connect a route to a specific slot in a target block
        
        Args:
            route: The route enum value
            target_block: The block to route to
            slot_name: The slot name in the target block
        """
        if route not in self.routes:
            raise ValueError(f"Route {route} does not exist in block {self.name}")
            
        if not hasattr(target_block, "slots") or slot_name not in target_block.slots:
            raise ValueError(f"Slot {slot_name} does not exist in target block {target_block.name}")
            
        # Store the connection
        self.routes[route]["connected_block_id"] = target_block.id
        self.routes[route]["connected_slot"] = slot_name
        
        self.log_event(
            f"Connected route {route} to slot {slot_name} in block {target_block.name}",
            "route_connected"
        )
    
    def trigger_route(self, route: Enum, data: Any = None) -> None:
        """
        Trigger a specific route with optional data
        
        Args:
            route: The route to trigger
            data: Optional data to pass
        """
        if route not in self.routes:
            raise ValueError(f"Route {route} does not exist in block {self.name}")
            
        connection = self.routes[route]
        if connection["connected_block_id"] is None:
            raise ValueError(f"Route {route} is not connected to any block")
            
        # Find the target block
        target_block = None
        for block in self.workflow.blocks:
            if block.id == connection["connected_block_id"]:
                target_block = block
                break
                
        if target_block is None:
            raise ValueError(f"Target block for route {route} not found")
            
        # Pass data to the target block
        if data is not None:
            target_block.receive_data(connection["connected_slot"], data)
        
        self.log_event(
            f"Triggered route {route} to block {target_block.name}",
            "route_triggered"
        )
    
    def requeue(self):
        """Requeue the block for execution"""
        if self.workflow:
            self.workflow.requeue_block(self)
    
    def reset(self):
        """Reset the block to its initial state"""
        # Reset all slots
        for slot in self.slots.values():
            slot["data"] = None
            
        self.payload = None
        self.log_event(f"Block {self.name} reset", "block_reset")

class LoopBlock(Block):
    def __init__(self, 
                 function: Callable,
                 input_schema: Dict[str, Type],
                 output_schema: Dict[str, Type],
                 compile_function: Optional[Callable] = None,
                 unpack_function: Optional[Callable] = None,
                 name: Optional[str] = None):
        """
        Initialize a loop block with input and output schemas
        
        Args:
            function: The function to execute in a loop
            input_schema: Dictionary mapping slot names to expected types
            output_schema: Dictionary mapping head names to output types
            compile_function: Optional function to transform input data before execution
            unpack_function: Optional function to transform output data before sending
            name: Optional block name (defaults to function name)
        """
        self.id = id(self)
        self.name = name or function.__name__
        self.function = function
        self.compile_function = compile_function
        self.unpack_function = unpack_function
        
        # Input slots
        self.slots = {
            key: {"type": type_val, "data": None, "connected_head": None} 
            for key, type_val in input_schema.items()
        }
        
        # Output heads
        self.heads = {
            key: {"type": type_val, "data": None, "connected_slots": []} 
            for key, type_val in output_schema.items()
        }
        
        self.payload = None
        self.workflow = None
        self.iteration_count = 0
        self.max_iterations = 100  # Default safety limit

    def execute(self):
        # TODO: Implement loop execution
        pass

    def validate(self):
        # TODO: Implement validation
        pass

def create_process_block(function: Callable,
                        input_schema: Optional[Dict[str, Type]] = None,
                        output_schema: Optional[Dict[str, Type]] = None,
                        compile_function: Optional[Callable] = None,
                        unpack_function: Optional[Callable] = None) -> FunctionBlock:
    """Factory function to create a function block"""
    # Infer output type from function signature if not provided
    if output_schema is None:
        from inspect import signature
        sig = signature(function)
        return_type = sig.return_annotation
        if return_type is not None:
            output_schema = {"main": return_type}
        else:
            output_schema = {"main": Any}
            
    # Create input schema if not provided
    if input_schema is None:
        from inspect import signature
        sig = signature(function)
        param_type = next(iter(sig.parameters.values())).annotation
        if param_type is not None:
            input_schema = {"main": param_type}
        else:
            input_schema = {"main": Any}
    
    return FunctionBlock(
        function=function,
        input_schema=input_schema,
        output_schema=output_schema,
        compile_function=compile_function,
        unpack_function=unpack_function
    )

def create_logic_block(function: Callable,
                      input_schema: Dict[str, Type],
                      route_enum: Type[Enum],
                      compile_function: Optional[Callable] = None,
                      unpack_function: Optional[Callable] = None) -> LogicBlock:
    """Factory function to create a logic block"""
    return LogicBlock(
        function=function,
        input_schema=input_schema,
        route_enum=route_enum,
        compile_function=compile_function,
        unpack_function=unpack_function
    )

class LinearProcessBlock(FunctionBlock):
    """A simplified FunctionBlock for linear workflows with single input/output"""
    def __init__(self, 
                 function: Callable,
                 name: Optional[str] = None):
        # Infer input/output types from function signature
        from inspect import signature
        sig = signature(function)
        input_type = next(iter(sig.parameters.values())).annotation
        output_type = sig.return_annotation
        
        super().__init__(
            function=function,
            input_schema={"main": input_type},
            output_schema={"main": output_type},
            name=name
        )
    
    def connect_linear(self, next_block: 'LinearProcessBlock'):
        """Connect this block's output to next block's input"""
        self.connect_head_to_slot("main", next_block, "main")






