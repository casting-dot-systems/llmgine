import pytest
from dataclasses import dataclass
from llmgine.workflows.workflow import Workflow, WorkflowContext
from llmgine.workflows.blocks import LinearProcessBlock
from llmgine.workflows.exceptions import WorkflowExecutionError

@dataclass
class InputData:
    value: int
    text: str

@dataclass
class OutputData:
    result: str

def test_workflow_creation():
    """Test basic workflow creation"""
    context = WorkflowContext(test_value="test")
    workflow = Workflow(global_context=context)
    assert workflow.global_context.get("test_value") == "test"
    assert len(workflow.execution_queue) == 0
    assert len(workflow.executed_blocks) == 0

def test_workflow_block_queuing():
    """Test block queuing functionality"""
    workflow = Workflow()
    
    def transform(data: InputData) -> OutputData:
        return OutputData(result=str(data.value))
    
    block = LinearProcessBlock(transform)
    workflow.queue_block(block)
    
    assert len(workflow.execution_queue) == 1
    assert block in workflow.execution_queue

def test_workflow_execution():
    """Test workflow execution with connected blocks"""
    workflow = Workflow()
    
    def transform1(data: InputData) -> OutputData:
        return OutputData(result=f"{data.text}_{data.value}")
    
    def transform2(data: OutputData) -> str:
        return f"Final: {data.result}"
    
    b1 = LinearProcessBlock(transform1)
    b2 = LinearProcessBlock(transform2)
    
    workflow.add_entry(b1.socket.slots["main"])
    b1.connect_linear(b2)
    workflow.add_exit(b2.plug.heads["main"])
    
    test_data = InputData(value=42, text="test")
    result = workflow.execute(test_data)
    
    assert result.data == "Final: test_42"
    assert len(result.execution_log) == 2
