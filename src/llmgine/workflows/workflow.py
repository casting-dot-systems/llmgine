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
                 execution_log: Optional[List[str]] = None, 
                 unpack_function: Optional[Callable] = None, 
                 compile_function: Optional[Callable] = None,
                 execution_mode: ExecutionMode = ExecutionMode.DEEP):
        self.global_context = global_context or WorkflowContext()
        self.execution_log = execution_log or []
        self.unpack_function = unpack_function
        self.compile_function = compile_function
        self.blocks: List[Block] = []
        self.start_block = None
        self.end_block = None
        self.execution_queue: Deque[Block] = deque()
        self.executed_blocks: List[Block] = []
        self.execution_mode = execution_mode

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
            
        # Reset state for new execution
        self.reset()
        
        # Apply any input transformation with unpack_function
        if self.unpack_function:
            try:
                unpacked_input = self.unpack_function(input_data)
                self.execution_log.append(f"Unpacked input: {input_data} -> {unpacked_input}")
            except Exception as e:
                raise WorkflowExecutionError(f"Error unpacking input data: {str(e)}")
        else:
            unpacked_input = input_data
        
        # Queue the start block for execution
        self.queue_block(self.start_block)
            
        # Pass input data to the start block(s)
        if hasattr(self.start_block, 'slots') and 'main' in self.start_block.slots:
            self.start_block.receive_data('main', unpacked_input)
        elif hasattr(self.start_block, 'slots') and len(self.start_block.slots) == 1:
            # If there's only one slot, use that
            slot_name = next(iter(self.start_block.slots))
            self.start_block.receive_data(slot_name, unpacked_input)
        elif isinstance(unpacked_input, dict) and hasattr(self.start_block, 'slots'):
            # If it's a dictionary input, try to match keys to slots
            matched = False
            for key, value in unpacked_input.items():
                if key in self.start_block.slots:
                    self.start_block.receive_data(key, value)
                    matched = True
            
            if not matched:
                raise WorkflowExecutionError(f"Cannot map input data keys to start block slots")
        else:
            raise WorkflowExecutionError(f"Cannot map input data to start block slots")
        
        # Process execution queue based on execution mode
        if self.execution_mode == ExecutionMode.DEEP:
            # Execute each branch to completion
            return self._execute_deep()
        elif self.execution_mode == ExecutionMode.WIDE:
            # Execute blocks more in parallel
            return self._execute_wide()
        else:
            raise WorkflowExecutionError(f"Unknown execution mode: {self.execution_mode}")
        
    def _execute_deep(self) -> WorkflowOutput:
        """Execute in deep mode - follow each branch to completion"""
        result = None
        
        while self.execution_queue:
            # Get the next block
            block = self.execution_queue.popleft()
            
            # Skip if already executed
            if block in self.executed_blocks:
                continue
            
            try:
                # Execute the block
                result = block.execute()
                self.execution_log.append(f"Executed block: {block.name}")
                self.executed_blocks.append(block)
            except Exception as e:
                raise WorkflowExecutionError(f"Error executing block {block.name}: {str(e)}")
        
        # If there's an end block, return its result
        if self.end_block and hasattr(self.end_block, 'heads'):
            for head_name, head in self.end_block.heads.items():
                if head.data is not None:
                    return WorkflowOutput(head.data, self.execution_log)
        
        return WorkflowOutput(result, self.execution_log)
    
    def _execute_wide(self) -> WorkflowOutput:
        """Execute in wide mode - execute blocks in breadth-first order"""
        result = None
        
        while self.execution_queue:
            # Get all blocks currently in the queue
            current_level_blocks = list(self.execution_queue)
            self.execution_queue.clear()
            
            # Execute all blocks at this level
            for block in current_level_blocks:
                # Skip if already executed
                if block in self.executed_blocks:
                    continue
                    
                try:
                    result = block.execute()
                    self.execution_log.append(f"Executed block: {block.name}")
                    self.executed_blocks.append(block)
                except Exception as e:
                    raise WorkflowExecutionError(f"Error executing block {block.name}: {str(e)}")
            
            # If no new blocks were queued, we're done
            if not self.execution_queue:
                break
        
        # If there's an end block, return its result
        if self.end_block and hasattr(self.end_block, 'heads'):
            for head_name, head in self.end_block.heads.items():
                if head.data is not None:
                    return WorkflowOutput(head.data, self.execution_log)
        
        return WorkflowOutput(result, self.execution_log)

    def visualize(self, output_path: str = "workflow.dot", view: bool = True):
        """
        Visualize the workflow as a graph
        
        Args:
            output_path: Path to save the visualization
            view: Whether to open the visualization
        """
        try:
            import graphviz
        except ImportError:
            raise ImportError("graphviz package is required for visualization. Install with 'pip install graphviz'")
            
        # Create digraph
        dot = graphviz.Digraph(comment="Workflow Visualization")
        
        # Add nodes
        for block in self.blocks:
            shape = "box"
            if hasattr(block, 'route_enum'):  # Logic block
                shape = "diamond"
            elif hasattr(block, 'iteration_count'):  # Loop block
                shape = "hexagon"
                
            label = block.name
            if block == self.start_block:
                label = f"START: {label}"
            if block == self.end_block:
                label = f"END: {label}"
                
            dot.node(str(block.id), label, shape=shape)
        
        # Add edges
        for block in self.blocks:
            if hasattr(block, 'heads') and isinstance(block.heads, dict):  # FunctionBlock or LoopBlock
                for head_name, head in block.heads.items():
                    if hasattr(head, 'connected_slot') and head.connected_slot:
                        target_block = head.connected_slot.block
                        dot.edge(
                            str(block.id), 
                            str(target_block.id), 
                            label=f"{head_name} → {head.connected_slot.name}"
                        )
            elif hasattr(block, 'routes'):  # LogicBlock
                for route, config in block.routes.items():
                    if config["target_block"] is not None:
                        dot.edge(
                            str(block.id),
                            str(config["target_block"].id),
                            label=f"{route.name} → {config['slot_name']}"
                        )
        
        # Save and optionally view
        try:
            dot.render(output_path, view=view)
            return f"Workflow visualization saved to {output_path}.pdf"
        except Exception as e:
            raise Exception(f"Error generating visualization: {str(e)}")
    
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
