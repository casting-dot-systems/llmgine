import pytest
from dataclasses import dataclass
from llmgine.workflows.attachments import Socket, Slot, Head, Plug
from llmgine.workflows.exceptions import CompileIncompleteSocketError

@dataclass
class TestData:
    value: int
    text: str

def test_socket_creation():
    """Test basic socket creation and slot initialization"""
    socket = Socket({"input": TestData})
    assert len(socket.slots) == 1
    assert isinstance(socket.slots["input"], Slot)
    assert socket.slots["input"].type == TestData

def test_socket_data_compilation():
    """Test socket data compilation"""
    socket = Socket({"input": TestData})
    test_data = TestData(value=42, text="test")
    socket.slots["input"].recieve_data(test_data)
    
    compiled = socket.compile_from_slots()
    assert isinstance(compiled, dict)
    assert compiled["input"] == test_data

def test_socket_incomplete_compilation():
    """Test compilation fails when not all slots have data"""
    socket = Socket({"input1": TestData, "input2": TestData})
    test_data = TestData(value=42, text="test")
    socket.slots["input1"].recieve_data(test_data)
    
    with pytest.raises(CompileIncompleteSocketError):
        socket.compile_from_slots()

def test_socket_custom_compilation():
    """Test socket with custom compile function"""
    def custom_compile(data: dict) -> str:
        return f"Compiled: {data['input'].text}"
        
    socket = Socket({"input": TestData})
    socket.custom_compile_function = custom_compile
    
    test_data = TestData(value=42, text="test")
    socket.slots["input"].recieve_data(test_data)
    
    compiled = socket.compile_from_slots()
    assert compiled == "Compiled: test"

def test_socket_reset():
    """Test socket reset functionality"""
    socket = Socket({"input": TestData})
    test_data = TestData(value=42, text="test")
    socket.slots["input"].recieve_data(test_data)
    
    socket.reset()
    assert socket.slots["input"].data is None
