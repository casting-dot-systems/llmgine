from dataclasses import dataclass
import pytest
import rich

from llmgine.workflows.blocks import FunctionBlock
from llmgine.workflows.attachments import DummyPlug, Socket, Plug
from llmgine.workflows.workflow import WorkflowFake


@dataclass
class InputData:
    value: int
    text: str


@dataclass
class OutputData:
    result: str

def transform(data: InputData) -> OutputData:
    return OutputData(result=f"{data.text}_{data.value}")

def transform2(data: OutputData) -> str:
    return data.result + "_v2"

def transform3(data: str) -> str:
    return data + "_v3"

def test_basic_process_block_creation():
    """Test basic creation of a process block"""

    def transform(data: InputData) -> OutputData:
        return OutputData(result=f"{data.text}_{data.value}")

    # main is the convention used for single input and output
    socket = Socket({"data": InputData})
    plug = Plug({"data": OutputData})

    def compile_function(data: InputData) -> OutputData:
        return OutputData(result=f"{data.text}_{data.value}")
    
    def unpack_function(data: OutputData) -> str:
        return data.result

    block = FunctionBlock(
        function=transform,
        socket=socket,
        plug=plug,
        compile_function=compile_function,
        unpack_function=unpack_function,
    )

    assert block.function == transform
    assert block.socket == socket
    assert block.plug == plug
    assert block.compile_function == compile_function
    assert block.unpack_function == unpack_function
    assert block.socket.block == block
    assert block.plug.block == block

def test_basic_process_block_execution():
    """Test basic execution of a process block"""

    workflow = WorkflowFake()
    
    block = workflow.add(
        FunctionBlock(
            function=transform,
            socket=Socket({"data": InputData}),
            plug=Plug({"data": OutputData}),
        ),
        start=True,
    )

    test_data = {"data": InputData(value=42, text="test")}
    result = block.raw_execute(test_data)

    assert result == OutputData(result="test_42")

def test_process_block_execution_with_data_from_slot():
    """Test execution of a process block with data from a slot"""
    workflow = WorkflowFake()
    
    block = workflow.add(
        FunctionBlock(
            function=transform,
            socket=Socket({"data": InputData}),
            plug=DummyPlug({"data": OutputData}),
        ),
        start=True,
        end=True,
    )
    
    test_data = InputData(value=42, text="test")
    block.socket.slots["data"].recieve_data(test_data)

    result = block.execute()

    assert result == OutputData(result="test_42")
    
def test_process_block_execution_with_compile_function():
    """Test execution of a process block with compile and unpack functions"""
    workflow = WorkflowFake()
    
    def compile_function(data: int) -> InputData:
        return {"data": InputData(value=data, text="test")}
    
    block = workflow.add(
        FunctionBlock(
            function=transform,
            socket=Socket({"data": int}),
            plug=DummyPlug({"data": OutputData}),
            compile_function=compile_function,
        ),
        start=True,
        end=True,
    )

    test_data = 42
    block.socket.slots["data"].recieve_data(test_data)

    result = block.execute()

    assert result == OutputData(result="test_42")

def test_process_block_with_unpack_function():
    """Test execution of a process block with an unpack function"""

    def unpack_function(data: OutputData) -> str:
        return {"data": data.result}
    
    workflow = WorkflowFake()
    
    block = workflow.add(
        FunctionBlock(
            function=transform,
            socket=Socket({"data": InputData}),
            plug=DummyPlug({"data": str}),
            unpack_function=unpack_function,
        ),
        start=True,
        end=True,
    )

    test_data = InputData(value=42, text="test")
    block.socket.slots["data"].recieve_data(test_data)

    block.execute()

    assert block.plug.passed_data["data"] == "test_42"

def test_connected_process_block_connection():
    """
    Tests the creation and connection of two process blocks, and their execution using a workflow
    """

    # Create workflow and add blocks
    workflow = WorkflowFake()
    b_transform1 = workflow.add(
        FunctionBlock(
            function=transform,
            socket=Socket({"data": InputData}),
            plug=Plug({"data": OutputData}),
        ),
        start=True,
    )

    b_transform2 = workflow.add(
        FunctionBlock(
            function=transform2,
            socket=Socket({"data": OutputData}),
            plug=Plug({"data": str}),
        )
    )
    
    b_transform3 = workflow.add(
        FunctionBlock(
            function=transform3,
            socket=Socket({"data": str}),
            plug=DummyPlug({"data": str}),
        ),
        end=True,
    )

    b_transform1.plug.heads["data"].connect(b_transform2.socket.slots["data"])
    b_transform2.plug.heads["data"].connect(b_transform3.socket.slots["data"])

    # Create test data
    test_data = InputData(value=42, text="test")

    # Execute workflow
    result = workflow.execute({"data": test_data})

    # Verify results
    assert len(workflow.execution_log) == 3
    rich.print(workflow.execution_log)
    assert isinstance(result, str)
    assert result == "test_42_v2_v3"