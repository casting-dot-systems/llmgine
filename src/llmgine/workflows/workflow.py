from __future__ import annotations
from typing import List, Optional, Callable, Any, Literal, Deque, Dict, Type
from collections import deque
from .exceptions import WorkflowExecutionError
from enum import Enum
from .blocks import WorkflowContext, Block
    

class ExecutionMode(Enum):
    DEEP = "deep"  # Execute each branch to completion before starting another
    WIDE = "wide"  # Execute blocks more in parallel

class WorkflowOutput:
    def __init__(self, data: Any, execution_log: List[str]):
        self.data = data
        self.execution_log = execution_log

def create_workflow(global_context: Optional[WorkflowContext] = None) -> 'Workflow':
    """Factory function to create a new workflow"""
    return Workflow(global_context=global_context)

class Workflow:
    def __init__(self, 
                 global_context: Optional[WorkflowContext] = None, 
                 execution_log: List[str] = [], 
                 unpack_function: Optional[Callable] = None, 
                 compile_function: Optional[Callable] = None):
        self.global_context = global_context
        self.execution_log = execution_log
        self.unpack_function = unpack_function
        self.compile_function = compile_function
        self.blocks: List[Block] = []
        self.start_block = None
        self.end_block = None
        self.execution_queue: Deque[Block] = deque()
        self.executed_blocks: List[Block] = []

    def add_block(self, block: Block) -> Block:
        """Add a block to the workflow"""
        self.blocks.append(block)
        block.set_workflow(self)
        return block
        
    def set_start_block(self, block: Block) -> None:
        """Set the starting block for the workflow"""
        if block not in self.blocks:
            self.add_block(block)
        self.start_block = block
        
    def set_end_block(self, block: Block) -> None:
        """Set the ending block for the workflow"""
        if block not in self.blocks:
            self.add_block(block)
        self.end_block = block
    
    def queue_block(self, block: Block) -> None:
        """Add a block to the execution queue"""
        if block not in self.execution_queue and block not in self.executed_blocks:
            self.execution_queue.append(block)
    
    def requeue_block(self, block: Block) -> None:
        """Requeue a block for execution"""
        if block in self.execution_queue:
            self.execution_queue.remove(block)
        self.execution_queue.append(block)
    
    def execute(self, input_data: Any) -> WorkflowOutput:
        """Execute the workflow with the given input data"""
        if not self.start_block:
            raise WorkflowExecutionError("No start block defined for workflow")
            
        # Pass input data to the start block
        # Assuming the start block has a 'main' slot
        self.start_block.receive_data("main", input_data)
        
        # Process execution queue
        while self.execution_queue:
            block = self.execution_queue.popleft()
            try:
                result = block.execute()
                self.execution_log.append(f"Executed block: {block.name}")
                self.executed_blocks.append(block)
            except Exception as e:
                raise WorkflowExecutionError(f"Error executing block: {str(e)}")
        
        # If there's an end block, return its result
        if self.end_block and hasattr(self.end_block, 'heads'):
            if 'main' in self.end_block.heads:
                return WorkflowOutput(self.end_block.heads['main']['data'], self.execution_log)
        
        return WorkflowOutput(result, self.execution_log)

    def visualize(self):
        # TODO: Implement visualization
        pass
    
    def validate(self):
        """Validate the workflow configuration"""
        if not self.start_block:
            raise WorkflowExecutionError("Workflow must have a start block")
        return True
        
    def reset(self):
        """Reset the workflow to its initial state"""
        for block in self.blocks:
            block.reset()
        self.execution_queue.clear()
        self.executed_blocks.clear()
        self.execution_log.clear()

class WorkflowFake:
    def __init__(self):
        self.blocks = []
        self.execution_log = []
        self.queue = []
        self.queuing_log = []
        self.start_block = None
        self.end_block = None
        
    def queue_block(self, block):
        if block not in self.queue:
            self.queue.append(block)
            self.queuing_log.append(f"Queued block: {block.name}")
    
    def requeue_block(self, block):
        if block in self.queue:
            self.queue.remove(block)
            self.queue.append(block)
            self.queuing_log.append(f"Requeued block: {block.name}")
        else:
            self.queue_block(block)
            
    @property
    def queue_size(self):
        return len(self.queue)
        
    @property
    def is_block_queued(self, block):
        return block in self.queue

    def execute_next(self):
        """Execute just the next block in queue"""
        if not self.queue:
            raise ValueError("No blocks in queue")
        block = self.queue.pop(0)
        result = block.execute()
        self.execution_log.append(f"Executed block: {block.name}")
        return result

    def execute(self, input_data=None):
        """Execute all blocks until the end block is reached"""
        if input_data is not None and self.start_block:
            # Use the new receive_data method instead of socket.compile_direct
            if hasattr(self.start_block, 'slots') and 'main' in self.start_block.slots:
                self.start_block.receive_data('main', input_data)
            elif len(self.start_block.slots) == 1:
                # If there's only one slot, use that
                slot_name = next(iter(self.start_block.slots))
                self.start_block.receive_data(slot_name, input_data)
            else:
                # If it's a dictionary input, try to match keys to slots
                if isinstance(input_data, dict):
                    for key, value in input_data.items():
                        if key in self.start_block.slots:
                            self.start_block.receive_data(key, value)
                
        while self.queue:
            result = self.execute_next()
            
        if self.end_block:
            # Get the result from the end block
            if hasattr(self.end_block, 'heads') and 'main' in self.end_block.heads:
                return self.end_block.heads['main']['data']
            return result
        else:
            raise WorkflowExecutionError("No end block defined")

    def add(self, 
            block: Block,
            start: bool = False,
            end: bool = False,
            **kwargs):
        self.blocks.append(block)
        block.workflow = self
        if start:
            self.start_block = block
        if end:
            self.end_block = block
        return block
