from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Optional, Tuple, Any, Dict, Type, List
from enum import Enum, auto
from abc import ABC, abstractmethod

from llmgine.messages.bus import MessageBus
from llmgine.workflows.attachments import Head, Slot
# Fix import path for observability
from ..observability import imprint, LogEvent
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
            queue: The execution queue
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
        self.payload = None
        self.workflow = None

        # Create slots
        self.slots = {}
        for key, type_val in input_schema.items():
            slot = Slot(name=key, type=type_val, block=self)
            self.slots[key] = slot
        
        # Create heads
        self.heads = {}
        for key, type_val in output_schema.items():
            head = Head(name=key, type=type_val, block=self)
            self.heads[key] = head

    def log_event(self, message: str, event_type: str, metadata: Optional[Dict[str, Any]] = None):
        if metadata:
            metadata["block_id"] = self.id
        imprint.emit(LogEvent(
            message=message,
            event_type=event_type,
            metadata=metadata or {"block_id": self.id}
        ))

    def set_workflow(self, workflow: Workflow):
        self.workflow = workflow
    
    def raw_execute(self, function_parameters: Dict[str, Any]) -> Any:
        """
        Execute the function directly with parameters and return the result
        Used for testing and debugging
        """
        results = self.function(**function_parameters)
        if self.unpack_function:
            results = self.unpack_function(results)
        return results

    def execute(self) -> Any:
        """Execute the function block and pass result to connected blocks"""
        try:
            # Before execution, try alternative approach to data handling
            # If we don't have a payload but do have data in slots
            if self.payload is None:
                self.log_event(f"Block {self.name} has no payload. Checking slots...", "missing_payload")
                
                # Check if we have any slot data
                slots_with_data = {name: slot.data for name, slot in self.slots.items() if slot.data is not None}
                if slots_with_data:
                    self.log_event(f"Found data in slots: {slots_with_data}", "found_slot_data")
                    
                    # Create payload directly from slot data
                    self.payload = slots_with_data
                    self.log_event(f"Created payload from slots: {self.payload}", "created_payload")
                else:
                    # Try compiling from slots one more time
                    self.check_and_compile_payload()
                
                # If we still don't have a payload, we can't execute
                if self.payload is None:
                    raise BlockExecutionError("Cannot execute block with no payload")
            
            self.state = FunctionBlockStates.EXECUTING
            self.log_event(f"Block {self.name} executing with payload: {self.payload}", "block_executing")
            
            # Execute the function with payload data
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
            
            self.state = FunctionBlockStates.COMPLETED    
            return result
            
        except Exception as e:
            self.state = FunctionBlockStates.FAILED
            self.log_event(f"Block {self.name} failed with error: {str(e)}", "block_failed")
            raise BlockExecutionError(f"Error executing block {self.name}: {str(e)}")

    def validate(self) -> bool:
        """Validate the block's configuration"""
        # Check that all required input slots have valid types
        for slot in self.slots.values():
            if not isinstance(slot.type, type):
                return False
        
        # Check that all output heads have valid types
        for head in self.heads.values():
            if not isinstance(head.type, type):
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
        
        # Store the data (type check happens in the slot)
        slot.receive_data(data)
        self.log_event(f"Slot {slot_name} received data: {data}", "slot_received_data")
        
        # Check if we can compile a complete payload
        self.check_and_compile_payload()
    
    def check_and_compile_payload(self) -> None:
        """Check if all required slots have data and compile them into a payload"""
        # Check if all slots have data
        self.log_event(f"Checking and compiling payload for block {self.name}", "checking_payload")
        for slot_name, slot in self.slots.items():
            self.log_event(f"Slot {slot_name} data: {slot.data}", "slot_data")
            
        all_slots_ready = all(slot.data is not None for slot in self.slots.values())
        if not all_slots_ready:
            self.log_event(f"Block {self.name} has incomplete inputs", "incomplete_inputs")
            self.incomplete_payload()
            return
            
        self.log_event(f"All slots have data for block {self.name}", "all_slots_ready")
            
        # Compile the payload
        if self.compile_function:
            # Custom compilation
            payload_data = {name: slot.data for name, slot in self.slots.items()}
            
            # Check if workflow_context is needed
            from inspect import signature
            sig = signature(self.compile_function)
            if "workflow_context" in sig.parameters:
                payload_data["workflow_context"] = self.workflow
                
            try:
                payload = self.compile_function(**payload_data)
                self.log_event(f"Used custom compilation to create payload: {payload}", "custom_compile")
            except Exception as e:
                self.log_event(f"Error compiling payload: {str(e)}", "compile_error")
                raise ValueError(f"Error compiling payload: {str(e)}")
        else:
            # Native compilation - just create a dictionary
            payload = {name: slot.data for name, slot in self.slots.items()}
            self.log_event(f"Created standard payload: {payload}", "standard_compile")
            
        self.complete_payload(payload)
    
    def incomplete_payload(self) -> None:
        """Handle incomplete payload - block isn't ready for execution yet"""
        self.state = FunctionBlockStates.AWAITING_INPUTS
    
    def complete_payload(self, payload: Dict[str, Any]) -> None:
        """
        Set the payload and prepare for execution
        
        Args:
            payload: The compiled payload
        """
        self.payload = payload
        self.state = FunctionBlockStates.READY
        self.log_event(f"Block {self.name} received payload: {payload}", "block_received_payload")
        self.requeue()
    
    def pass_data_to_connected_slots(self, data: Any) -> None:
        """
        Pass data to connected slots in other blocks
        
        Args:
            data: Data to pass
        """
        self.log_event(f"Passing data to connected slots: {data}", "passing_data")
        for head_name, head in self.heads.items():
            # Store data in the head
            head.data = data
            
            # Pass data to connected slot if exists
            if head.connected_slot and head.connected_slot.block in self.workflow.blocks:
                target_block = head.connected_slot.block
                self.log_event(
                    f"Head {head_name} sending data to slot {head.connected_slot.name} in block {target_block.name}", 
                    "head_sending_data"
                )
                
                # First send the data
                head.send_data(data)
                
                # Then explicitly queue the target block
                if self.workflow:
                    self.workflow.queue_block(target_block)
                    self.log_event(
                        f"Queued target block {target_block.name} for execution", 
                        "target_block_queued"
                    )
    
    def connect_head_to_slot(self, head_name: str, target_block: 'Block', slot_name: str) -> None:
        """
        Connect a head to a slot in another block
        
        Args:
            head_name: Name of the head to connect
            target_block: Block to connect to
            slot_name: Name of the slot to connect to
        """
        if head_name not in self.heads:
            raise ValueError(f"Head {head_name} does not exist in block {self.name}")
            
        if not hasattr(target_block, 'slots') or slot_name not in target_block.slots:
            raise ValueError(f"Slot {slot_name} does not exist in block {target_block.name}")
            
        # Connect using direct references
        head = self.heads[head_name]
        slot = target_block.slots[slot_name]
        head.connect(slot)
        
        self.log_event(
            f"Connected head {head_name} to slot {slot_name} in block {target_block.name}",
            "connection_established"
        )
    
    def requeue(self):
        """Requeue the block for execution"""
        if self.workflow:
            self.workflow.queue_block(self)
    
    def reset(self):
        """Reset the block to its initial state"""
        # Reset all slots
        for slot in self.slots.values():
            slot.data = None
            
        # Reset all heads
        for head in self.heads.values():
            head.data = None
        
        self.payload = None
        self.state = FunctionBlockStates.NEW
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
        self.state = FunctionBlockStates.NEW
        self.payload = None
        self.workflow = None
        
        # Create slots
        self.slots = {}
        for key, type_val in input_schema.items():
            slot = Slot(name=key, type=type_val, block=self)
            self.slots[key] = slot
        
        # Store routes configuration
        self.route_enum = route_enum
        self.routes = {}
        for route in route_enum:
            self.routes[route] = {
                "target_block": None,
                "slot_name": None
            }

    def log_event(self, message: str, event_type: str, metadata: Optional[Dict[str, Any]] = None):
        if metadata:
            metadata["block_id"] = self.id
        imprint.emit(LogEvent(
            message=message,
            event_type=event_type,
            metadata=metadata or {"block_id": self.id}
        ))

    def set_workflow(self, workflow: Workflow):
        self.workflow = workflow

    def execute(self) -> Tuple[Any, Enum]:
        """Execute the logic block and route output to the appropriate block"""
        try:
            # Make sure we have all needed inputs
            input_complete = all(slot.data is not None for slot in self.slots.values())
            if not input_complete:
                self.log_event(f"Logic block {self.name} missing required inputs", "missing_inputs")
                self.state = FunctionBlockStates.AWAITING_INPUTS
                raise BlockExecutionError("Logic block is missing required inputs")
                
            self.state = FunctionBlockStates.EXECUTING
            
            # Validate before execution
            self.validate()
            
            # Get the data directly from the slot, not as a dictionary
            # This is the key fix - we need to get the actual QueryInfo object
            # from our slot, not wrap it in another dictionary
            slot_name = next(iter(self.slots.keys()))  # Get first slot name
            data_to_pass = self.slots[slot_name].data
            
            self.log_event(f"Logic block {self.name} extracted direct data: {data_to_pass}", "logic_block_data_extract")
                
            # Execute the function with direct data
            self.log_event(f"Logic block {self.name} executing with data: {data_to_pass}", "logic_block_executing")
            result = self.function(data_to_pass)
            
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
            self.trigger_route(decision, data_to_pass)  # Pass the original data from the slot
            
            self.state = FunctionBlockStates.COMPLETED
            return result
            
        except Exception as e:
            self.state = FunctionBlockStates.FAILED
            self.log_event(f"Logic block {self.name} failed with error: {str(e)}", "logic_block_failed")
            raise BlockExecutionError(f"Error executing logic block {self.name}: {str(e)}")

    def validate(self) -> bool:
        """Validate the logic block's configuration"""
        # Check that all required input slots have valid types
        for slot in self.slots.values():
            if not isinstance(slot.type, type):
                return False
                
        # Check that all routes are connected
        for route, config in self.routes.items():
            if config["target_block"] is None or config["slot_name"] is None:
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
        
        # Store the data (type check happens in the slot)
        slot.receive_data(data)
        self.log_event(f"Slot {slot_name} received data: {data}", "slot_received_data")
        
        # Check if we can execute
        self.check_and_compile_payload()
    
    def check_and_compile_payload(self) -> None:
        """Check if all required slots have data and compile them into a payload"""
        # Check if all slots have data
        if not all(slot.data is not None for slot in self.slots.values()):
            self.state = FunctionBlockStates.AWAITING_INPUTS
            return
        
        # Mark ready and queue for execution
        self.state = FunctionBlockStates.READY
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
        self.routes[route]["target_block"] = target_block
        self.routes[route]["slot_name"] = slot_name
        
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
        if connection["target_block"] is None:
            raise ValueError(f"Route {route} is not connected to any block")
            
        target_block = connection["target_block"]
        target_slot = connection["slot_name"]
        
        self.log_event(
            f"Triggering route {route} to slot {target_slot} in block {target_block.name}",
            "route_triggering"
        )
            
        # Force function blocks to have a payload, that's the issue!
        if isinstance(target_block, FunctionBlock):
            # Create a payload directly
            target_block.payload = {target_slot: data}
            self.log_event(f"Forced payload for target block: {target_block.payload}", "force_payload")
            
        # Still, pass data to the target block slot
        if hasattr(target_block, "slots"):
            target_block.receive_data(target_slot, data)
        
        # Explicitly queue the target block for execution
        if self.workflow:
            self.workflow.queue_block(target_block)
            self.log_event(
                f"Queued target block {target_block.name} for execution via route {route}",
                "target_block_queued"
            )
        
        self.log_event(
            f"Triggered route {route} to slot {target_slot} in block {target_block.name}",
            "route_triggered"
        )
    
    def requeue(self):
        """Requeue the block for execution"""
        if self.workflow:
            self.workflow.queue_block(self)
    
    def reset(self):
        """Reset the block to its initial state"""
        # Reset all slots
        for slot in self.slots.values():
            slot.data = None
            
        self.payload = None
        self.state = FunctionBlockStates.NEW
        self.log_event(f"Block {self.name} reset", "block_reset")

class LoopBlock(Block):
    def __init__(self, 
                 function: Callable,
                 input_schema: Dict[str, Type],
                 output_schema: Dict[str, Type],
                 termination_condition: Callable[[Any, int], bool] = None,
                 compile_function: Optional[Callable] = None,
                 unpack_function: Optional[Callable] = None,
                 max_iterations: int = 100,
                 queue: Optional[Queue] = None,
                 name: Optional[str] = None):
        """
        Initialize a loop block with input and output schemas
        
        Args:
            function: The function to execute in a loop
            input_schema: Dictionary mapping slot names to expected types
            output_schema: Dictionary mapping head names to output types
            termination_condition: Optional function to determine when to exit the loop
                                  Takes result and iteration count, returns True when loop should end
            compile_function: Optional function to transform input data before execution
            unpack_function: Optional function to transform output data before sending
            max_iterations: Maximum number of iterations (safety limit)
            queue: Optional execution queue
            name: Optional block name (defaults to function name)
        """
        self.id = id(self)
        self.name = name or function.__name__
        self.function = function
        self.compile_function = compile_function
        self.unpack_function = unpack_function
        self.termination_condition = termination_condition
        self.queue = queue or Queue()
        self.payload = None
        self.workflow = None
        self.iteration_count = 0
        self.max_iterations = max_iterations
        self.loop_state = None
        self.message_bus = MessageBus()
        self.state = FunctionBlockStates.NEW

        # Create slots
        self.slots = {}
        for key, type_val in input_schema.items():
            slot = Slot(name=key, type=type_val, block=self)
            self.slots[key] = slot
        
        # Create heads
        self.heads = {}
        for key, type_val in output_schema.items():
            head = Head(name=key, type=type_val, block=self)
            self.heads[key] = head

    def log_event(self, message: str, event_type: str, metadata: Optional[Dict[str, Any]] = None):
        if metadata:
            metadata["block_id"] = self.id
        imprint.emit(LogEvent(
            message=message,
            event_type=event_type,
            metadata=metadata or {"block_id": self.id}
        ))

    def set_workflow(self, workflow: Workflow):
        self.workflow = workflow

    def execute(self) -> Any:
        """Execute the function in a loop until termination condition is met"""
        try:
            # Make sure we have inputs on first iteration
            if self.iteration_count == 0:
                input_complete = all(slot.data is not None for slot in self.slots.values()) 
                if not input_complete:
                    self.log_event(f"Loop block {self.name} missing required inputs", "missing_loop_inputs")
                    self.state = FunctionBlockStates.AWAITING_INPUTS
                    raise BlockExecutionError("Loop block is missing required inputs")
            
            self.state = FunctionBlockStates.EXECUTING
            self.log_event(f"Loop block {self.name} starting execution", "loop_block_starting")
            
            # First time or continuing loop?
            if self.iteration_count == 0:
                # First iteration - get input data from slots or payload
                if self.payload is not None:
                    input_data = self.payload
                    self.log_event(f"Loop block using existing payload: {input_data}", "loop_using_payload")
                else:
                    # Get data from slots directly
                    slot_name = next(iter(self.slots.keys()))  # Get first slot name
                    input_data = self.slots[slot_name].data
                    
                    # If it's a dictionary with the slot name, use the value
                    if isinstance(input_data, dict) and slot_name in input_data:
                        input_data = input_data[slot_name]
                    
                    self.log_event(f"Loop block using direct slot data: {input_data}", "loop_using_slot_data")
                
                # Apply compile function if provided
                if self.compile_function:
                    try:
                        input_data = self.compile_function(input_data)
                        self.log_event(f"Loop block used custom compilation: {input_data}", "loop_custom_compile")
                    except Exception as e:
                        self.log_event(f"Error compiling input data: {str(e)}", "loop_compile_error")
                        raise ValueError(f"Error compiling input data: {str(e)}")
            else:
                # Continuing - use loop state from previous iteration
                input_data = self.loop_state
                self.log_event(f"Loop iteration {self.iteration_count} using previous state: {input_data}", "loop_using_state")
            
            self.log_event(
                f"Loop block {self.name} iteration {self.iteration_count} executing with data: {input_data}", 
                "loop_iteration_executing"
            )
            
            # Execute the function
            result = self.function(input_data)
            
            # Store result as loop state for next iteration
            self.loop_state = result
            
            # Increase iteration count
            self.iteration_count += 1
            
            # Check termination condition
            should_terminate = False
            
            # Check custom termination condition if provided
            if self.termination_condition:
                try:
                    should_terminate = self.termination_condition(result, self.iteration_count)
                    self.log_event(
                        f"Termination condition result: {should_terminate}", 
                        "loop_termination_check"
                    )
                except Exception as e:
                    self.log_event(
                        f"Error in termination condition: {str(e)}", 
                        "loop_termination_error"
                    )
                    # Force termination on error
                    should_terminate = True
            
            # Always check max iterations as a safety limit
            if self.iteration_count >= self.max_iterations:
                self.log_event(
                    f"Loop block {self.name} reached maximum iterations ({self.max_iterations})", 
                    "loop_max_iterations"
                )
                should_terminate = True
                
            # Hard-code termination after 10 iterations for safety 
            if self.iteration_count >= 10:
                self.log_event(
                    f"Loop block {self.name} reached 10 iterations, forcing termination", 
                    "loop_force_terminate"
                )
                should_terminate = True
            
            if should_terminate:
                self.log_event(
                    f"Loop block {self.name} terminating after {self.iteration_count} iterations", 
                    "loop_terminating"
                )
                
                # Apply unpack function if provided before passing to connected blocks
                if self.unpack_function:
                    output_data = self.unpack_function(result)
                    self.log_event(
                        f"Loop block {self.name} result unpacked to: {output_data}", 
                        "loop_result_unpacked"
                    )
                else:
                    output_data = result
                
                # Pass final result to output heads
                self.log_event(f"Passing final loop result to output: {output_data}", "loop_passing_result")
                self.pass_data_to_connected_slots(output_data)
                
                # Force the next block to execute by queueing it
                for head_name, head in self.heads.items():
                    if head.connected_slot and head.connected_slot.block:
                        next_block = head.connected_slot.block
                        if self.workflow:
                            self.workflow.queue_block(next_block)
                            self.log_event(f"Explicitly queuing next block {next_block.name}", "loop_queue_next")
                
                self.state = FunctionBlockStates.COMPLETED
                return result
            else:
                # Requeue for next iteration
                self.log_event(
                    f"Loop block {self.name} iteration {self.iteration_count} complete, requeuing", 
                    "loop_iteration_complete"
                )
                self.requeue()
                return None
        
        except Exception as e:
            self.log_event(f"Loop block {self.name} failed with error: {str(e)}", "loop_block_failed")
            self.state = FunctionBlockStates.FAILED
            raise BlockExecutionError(f"Error executing loop block {self.name}: {str(e)}")

    def validate(self) -> bool:
        """Validate the loop block's configuration"""
        # Check that all required input slots have valid types
        for slot in self.slots.values():
            if not isinstance(slot.type, type):
                return False
        
        # Check that all output heads have valid types
        for head in self.heads.values():
            if not isinstance(head.type, type):
                return False
        
        # Ensure max_iterations is positive
        if self.max_iterations <= 0:
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
        
        # Store the data (type check happens in the slot)
        slot.receive_data(data)
        self.log_event(f"Slot {slot_name} received data: {data}", "slot_received_data")
        
        # Check if we can compile a complete payload
        self.check_and_compile_payload()
    
    def check_and_compile_payload(self) -> None:
        """Check if all required slots have data and compile them into a payload"""
        # Check if all slots have data
        self.log_event(f"Checking and compiling payload for loop block {self.name}", "checking_loop_payload")
        for slot_name, slot in self.slots.items():
            self.log_event(f"Slot {slot_name} data: {slot.data}", "loop_slot_data")
        
        if not all(slot.data is not None for slot in self.slots.values()):
            self.log_event(f"Loop block {self.name} has incomplete inputs", "incomplete_loop_inputs")
            self.state = FunctionBlockStates.AWAITING_INPUTS
            return
        
        self.log_event(f"All slots have data for loop block {self.name}", "all_loop_slots_ready")
            
        # Reset iteration counter for a new execution 
        self.iteration_count = 0
        self.loop_state = None
        
        # Create payload for first iteration
        self.payload = {name: slot.data for name, slot in self.slots.items()}
        self.log_event(f"Created initial loop payload: {self.payload}", "loop_payload_created")
        
        # Mark ready and queue for execution
        self.state = FunctionBlockStates.READY
        self.requeue()
    
    def pass_data_to_connected_slots(self, data: Any) -> None:
        """
        Pass data to connected slots in other blocks
        
        Args:
            data: Data to pass
        """
        self.log_event(f"Loop block passing data to connected slots: {data}", "loop_passing_data")
        for head_name, head in self.heads.items():
            # Store data in the head
            head.data = data
            
            # Pass data to connected slot if exists
            if head.connected_slot and head.connected_slot.block in self.workflow.blocks:
                target_block = head.connected_slot.block
                self.log_event(
                    f"Loop block head {head_name} sending data to slot {head.connected_slot.name} in block {target_block.name}", 
                    "loop_head_sending_data"
                )
                
                # First send the data
                head.send_data(data)
                
                # Then explicitly queue the target block
                if self.workflow:
                    self.workflow.queue_block(target_block)
                    self.log_event(
                        f"Queued target block {target_block.name} for execution from loop block", 
                        "loop_target_block_queued"
                    )
    
    def connect_head_to_slot(self, head_name: str, target_block: Block, slot_name: str) -> None:
        """
        Connect a head to a slot in another block
        
        Args:
            head_name: Name of the head to connect
            target_block: Block to connect to
            slot_name: Name of the slot to connect to
        """
        if head_name not in self.heads:
            raise ValueError(f"Head {head_name} does not exist in block {self.name}")
            
        if not hasattr(target_block, "slots") or slot_name not in target_block.slots:
            raise ValueError(f"Slot {slot_name} does not exist in block {target_block.name}")
            
        # Connect using direct references
        head = self.heads[head_name]
        slot = target_block.slots[slot_name]
        head.connect(slot)
        
        self.log_event(
            f"Connected head {head_name} to slot {slot_name} in block {target_block.name}",
            "connection_established"
        )
    
    def requeue(self):
        """Requeue the block for execution"""
        if self.workflow:
            self.workflow.queue_block(self)
    
    def reset(self):
        """Reset the block to its initial state"""
        # Reset all slots
        for slot in self.slots.values():
            slot.data = None
            
        # Reset all heads
        for head in self.heads.values():
            head.data = None
            
        self.payload = None
        self.iteration_count = 0
        self.loop_state = None
        self.state = FunctionBlockStates.NEW
        self.log_event(f"Block {self.name} reset", "block_reset")

def create_function_block(function: Callable,
                        input_schema: Dict[str, Type],
                        output_schema: Dict[str, Type],
                        compile_function: Optional[Callable] = None,
                        unpack_function: Optional[Callable] = None,
                        name: Optional[str] = None,
                        queue: Optional[Queue] = None) -> FunctionBlock:
    """Factory function to create a function block"""
    # Create default queue if not provided
    if queue is None:
        queue = Queue()
    
    return FunctionBlock(
        function=function,
        input_schema=input_schema,
        output_schema=output_schema,
        queue=queue,
        compile_function=compile_function,
        unpack_function=unpack_function,
        name=name
    )

def create_process_block(function: Callable,
                        input_schema: Optional[Dict[str, Type]] = None,
                        output_schema: Optional[Dict[str, Type]] = None,
                        compile_function: Optional[Callable] = None,
                        unpack_function: Optional[Callable] = None,
                        queue: Optional[Queue] = None,
                        name: Optional[str] = None) -> FunctionBlock:
    """
    Factory function to create a function block, inferring schemas from function signature
    
    Args:
        function: The function to execute
        input_schema: Optional dictionary mapping slot names to expected types
        output_schema: Optional dictionary mapping head names to output types
        compile_function: Optional function to transform input data before execution
        unpack_function: Optional function to transform output data before sending
        queue: Optional execution queue
        name: Optional block name (defaults to function name)
    
    Returns:
        A FunctionBlock configured with the provided parameters
    """
    # Create default queue if not provided
    if queue is None:
        queue = Queue()
        
    # Infer output type from function signature if not provided
    if output_schema is None:
        from inspect import signature
        sig = signature(function)
        return_type = sig.return_annotation
        if return_type is not None and return_type is not sig.empty:
            output_schema = {"main": return_type}
        else:
            output_schema = {"main": Any}
            
    # Create input schema if not provided
    if input_schema is None:
        from inspect import signature
        sig = signature(function)
        
        if sig.parameters:
            param = next(iter(sig.parameters.values()))
            param_type = param.annotation
            if param_type is not None and param_type is not sig.empty:
                input_schema = {"main": param_type}
            else:
                input_schema = {"main": Any}
        else:
            input_schema = {"main": Any}
    
    return FunctionBlock(
        function=function,
        input_schema=input_schema,
        output_schema=output_schema,
        queue=queue,
        compile_function=compile_function,
        unpack_function=unpack_function,
        name=name
    )

def create_logic_block(function: Callable,
                      input_schema: Dict[str, Type],
                      route_enum: Type[Enum],
                      compile_function: Optional[Callable] = None,
                      unpack_function: Optional[Callable] = None,
                      name: Optional[str] = None) -> LogicBlock:
    """
    Factory function to create a logic block
    
    Args:
        function: The function to execute
        input_schema: Dictionary mapping slot names to expected types
        route_enum: Enum type for routing decisions
        compile_function: Optional function to transform input data before execution
        unpack_function: Optional function to transform output data before routing
        name: Optional block name (defaults to function name)
        
    Returns:
        A LogicBlock configured with the provided parameters
    """
    return LogicBlock(
        function=function,
        input_schema=input_schema,
        route_enum=route_enum,
        compile_function=compile_function,
        unpack_function=unpack_function,
        name=name
    )

def create_loop_block(function: Callable,
                    input_schema: Dict[str, Type],
                    output_schema: Dict[str, Type],
                    termination_condition: Optional[Callable[[Any, int], bool]] = None,
                    compile_function: Optional[Callable] = None,
                    unpack_function: Optional[Callable] = None,
                    max_iterations: int = 100,
                    queue: Optional[Queue] = None,
                    name: Optional[str] = None) -> LoopBlock:
    """
    Factory function to create a loop block
    
    Args:
        function: The function to execute in a loop
        input_schema: Dictionary mapping slot names to expected types
        output_schema: Dictionary mapping head names to output types
        termination_condition: Optional function to determine when to exit the loop
                              Takes result and iteration count, returns True when loop should end
        compile_function: Optional function to transform input data before execution
        unpack_function: Optional function to transform output data before sending
        max_iterations: Maximum number of iterations (safety limit)
        queue: Optional execution queue
        name: Optional block name (defaults to function name)
        
    Returns:
        A LoopBlock configured with the provided parameters
    """
    # Create default queue if not provided
    if queue is None:
        queue = Queue()
        
    return LoopBlock(
        function=function,
        input_schema=input_schema,
        output_schema=output_schema,
        termination_condition=termination_condition,
        compile_function=compile_function,
        unpack_function=unpack_function,
        max_iterations=max_iterations,
        queue=queue,
        name=name
    )
    
class LLMBlock(FunctionBlock):
    """A specialized FunctionBlock for LLM interactions"""
    def __init__(self, 
                 llm_function: Callable,
                 input_schema: Dict[str, Type],
                 output_schema: Dict[str, Type],
                 system_prompt: Optional[str] = None,
                 model: Optional[str] = None,
                 compile_function: Optional[Callable] = None,
                 unpack_function: Optional[Callable] = None,
                 name: Optional[str] = None,
                 queue: Optional[Queue] = None):
        """
        Initialize an LLM block with input and output schemas
        
        Args:
            llm_function: The function to execute LLM calls
            input_schema: Dictionary mapping slot names to expected types
            output_schema: Dictionary mapping head names to output types
            system_prompt: Optional system prompt for the LLM
            model: Optional model identifier
            compile_function: Optional function to transform input data before execution
            unpack_function: Optional function to transform output data before sending
            name: Optional block name (defaults to function name)
            queue: Optional execution queue
        """
        super().__init__(
            function=llm_function,
            input_schema=input_schema,
            output_schema=output_schema,
            queue=queue,
            compile_function=compile_function,
            unpack_function=unpack_function,
            name=name or llm_function.__name__
        )
        
        self.system_prompt = system_prompt
        self.model = model
        self.execution_history = []

    def execute(self) -> Any:
        """Execute the LLM call and pass result to connected blocks"""
        try:
            self.state = FunctionBlockStates.EXECUTING
            self.log_event(f"LLM block {self.name} executing with payload: {self.payload}", "llm_executing")
            
            # Add system prompt and model to payload if available
            execution_payload = dict(self.payload)
            if self.system_prompt:
                execution_payload["system_prompt"] = self.system_prompt
            if self.model:
                execution_payload["model"] = self.model
                
            # Execute the LLM call
            result = self.function(**execution_payload)
            
            # Store in execution history
            self.execution_history.append({
                "input": execution_payload,
                "output": result
            })
            
            self.log_event(f"LLM block {self.name} executed with result: {result}", "llm_executed")
            
            # Apply unpack function if provided before passing to connected blocks
            if self.unpack_function:
                output_data = self.unpack_function(result)
                self.log_event(f"LLM block {self.name} result unpacked to: {output_data}", "llm_unpacked")
            else:
                output_data = result
                
            # Store the result in heads and pass to connected slots
            self.pass_data_to_connected_slots(output_data)
            
            self.state = FunctionBlockStates.COMPLETED
            return result
            
        except Exception as e:
            self.log_event(f"LLM block {self.name} failed with error: {str(e)}", "llm_failed")
            self.state = FunctionBlockStates.FAILED
            raise BlockExecutionError(f"Error executing LLM block: {str(e)}")
            
def create_llm_block(
    llm_function: Callable,
    input_schema: Dict[str, Type],
    output_schema: Dict[str, Type],
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    compile_function: Optional[Callable] = None,
    unpack_function: Optional[Callable] = None,
    name: Optional[str] = None,
    queue: Optional[Queue] = None
) -> LLMBlock:
    """Factory function to create an LLM block"""
    # Create default queue if not provided
    if queue is None:
        queue = Queue()
    
    return LLMBlock(
        llm_function=llm_function,
        input_schema=input_schema,
        output_schema=output_schema,
        system_prompt=system_prompt,
        model=model,
        compile_function=compile_function,
        unpack_function=unpack_function,
        name=name,
        queue=queue
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






