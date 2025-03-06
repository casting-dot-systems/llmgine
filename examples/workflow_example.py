#!/usr/bin/env python3
"""
Workflow example using llmgine.

This example demonstrates a multi-step workflow that:
1. Takes a user query about weather
2. Uses an LLM to extract location and time
3. Makes a decision about how to handle the query
4. Executes different actions based on the decision
5. Returns a formatted response to the user
"""

import sys
import os

# Add the src directory to the path so we can import llmgine
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional

from llmgine.workflows.workflow import Workflow, ExecutionMode
from llmgine.workflows.blocks import (
    create_function_block, create_logic_block, create_loop_block, FunctionBlock
)
from llmgine.types.utils import Queue

# Define data models
@dataclass
class WeatherQuery:
    """User query about weather"""
    raw_query: str

@dataclass
class QueryInfo:
    """Structured information extracted from the query"""
    location: str
    time_period: str
    query_type: str
    original_query: str

@dataclass
class WeatherData:
    """Weather information for a location"""
    temperature: float
    conditions: str
    location: str
    time_period: str

class QueryAction(Enum):
    """Possible actions to take based on the query"""
    FETCH_WEATHER = "fetch_weather"
    ASK_FOR_CLARIFICATION = "ask_for_clarification"
    ERROR_UNSUPPORTED = "error_unsupported"


# Define workflow functions
def extract_info_from_query(query: WeatherQuery) -> QueryInfo:
    """
    LLM function to extract structured information from a weather query.
    In a real application, this would call an actual LLM.
    """
    # This is a mock LLM response - in a real app, this would use an actual LLM
    print(f"Extracting information from: {query.raw_query}")
    
    # Simple keyword-based extraction for the example
    location = "New York"
    if "tokyo" in query.raw_query.lower():
        location = "Tokyo"
    elif "paris" in query.raw_query.lower():
        location = "Paris"
    elif "london" in query.raw_query.lower():
        location = "London"
    
    time_period = "today"
    if "tomorrow" in query.raw_query.lower():
        time_period = "tomorrow"
    elif "weekend" in query.raw_query.lower():
        time_period = "weekend"
    
    query_type = "weather"
    if "rain" in query.raw_query.lower() or "sunny" in query.raw_query.lower():
        query_type = "weather_condition"
    elif "temperature" in query.raw_query.lower() or "hot" in query.raw_query.lower() or "cold" in query.raw_query.lower():
        query_type = "temperature"
    
    return QueryInfo(
        location=location,
        time_period=time_period,
        query_type=query_type,
        original_query=query.raw_query
    )


def decide_action(input_data: Any) -> Tuple[None, QueryAction]:
    """Decide what action to take based on the query information"""
    # Handle both dictionary and direct input
    if isinstance(input_data, dict) and "query_info" in input_data:
        query_info = input_data["query_info"]
    else:
        query_info = input_data
        
    print(f"Deciding action for: {query_info}")
    
    # Simple decision logic
    if not query_info.location or query_info.location == "unknown":
        return None, QueryAction.ASK_FOR_CLARIFICATION
    
    if query_info.query_type not in ["weather", "weather_condition", "temperature"]:
        return None, QueryAction.ERROR_UNSUPPORTED
    
    return None, QueryAction.FETCH_WEATHER


def fetch_weather(query_info: Any) -> WeatherData:
    """Fetch weather data for the location and time period"""
    # Type safety - ensure query_info is valid
    if not hasattr(query_info, 'location'):
        raise ValueError(f"Invalid query_info: {query_info}")
        
    print(f"Fetching weather for {query_info.location} ({query_info.time_period})")
    
    # Mock weather data - in a real app, this would call a weather API
    weather_data = {
        "New York": {"today": (72, "Sunny"), "tomorrow": (68, "Partly Cloudy"), "weekend": (65, "Rainy")},
        "Tokyo": {"today": (68, "Cloudy"), "tomorrow": (72, "Sunny"), "weekend": (70, "Partly Cloudy")},
        "Paris": {"today": (62, "Rainy"), "tomorrow": (65, "Cloudy"), "weekend": (70, "Sunny")},
        "London": {"today": (60, "Rainy"), "tomorrow": (62, "Cloudy"), "weekend": (65, "Partly Cloudy")}
    }
    
    location = query_info.location if query_info.location in weather_data else "New York"
    time_period = query_info.time_period if query_info.time_period in weather_data[location] else "today"
    
    temp, conditions = weather_data[location][time_period]
    
    return WeatherData(
        temperature=temp,
        conditions=conditions,
        location=location,
        time_period=time_period
    )


def ask_for_clarification(query_info: Any) -> str:
    """Generate a clarification request"""
    # Type safety - ensure query_info is valid
    if not hasattr(query_info, 'location'):
        raise ValueError(f"Invalid query_info: {query_info}")
        
    if not query_info.location or query_info.location == "unknown":
        return "I need to know which location you're asking about. Could you please specify a city?"
    
    if not query_info.time_period or query_info.time_period == "unknown":
        return f"When would you like to know the weather for {query_info.location}? Today, tomorrow, or this weekend?"
    
    return "I didn't quite understand your question. Could you rephrase it?"


def error_unsupported(query_info: Any) -> str:
    """Generate an error message for unsupported queries"""
    # Type safety - ensure query_info is valid
    if not hasattr(query_info, 'query_type'):
        raise ValueError(f"Invalid query_info: {query_info}")
        
    return f"Sorry, I can only answer questions about weather conditions and temperatures. Your query type '{query_info.query_type}' is not supported."


def format_weather_response(weather_data: Any) -> str:
    """Format the weather data into a user-friendly response"""
    # Type safety - ensure weather_data is valid
    if not hasattr(weather_data, 'location') or not hasattr(weather_data, 'conditions'):
        raise ValueError(f"Invalid weather_data: {weather_data}")
        
    return f"The weather in {weather_data.location} {weather_data.time_period} is {weather_data.conditions} with a temperature of {weather_data.temperature}°F."


def create_weather_workflow():
    """Create and return the weather query workflow"""
    # Create a new workflow
    workflow = Workflow(execution_mode=ExecutionMode.DEEP)
    
    # Create a shared queue for all blocks
    shared_queue = Queue()
    
    # Create blocks
    extract_info_block = create_function_block(
        function=extract_info_from_query,
        input_schema={"query": WeatherQuery},
        output_schema={"query_info": QueryInfo},
        queue=shared_queue
    )
    
    decision_block = create_logic_block(
        function=decide_action,
        input_schema={"query_info": QueryInfo},
        route_enum=QueryAction
    )
    
    fetch_weather_block = create_function_block(
        function=fetch_weather,
        input_schema={"query_info": QueryInfo},
        output_schema={"weather_data": WeatherData},
        queue=shared_queue
    )
    
    ask_clarification_block = create_function_block(
        function=ask_for_clarification,
        input_schema={"query_info": QueryInfo},
        output_schema={"response": str},
        queue=shared_queue
    )
    
    error_block = create_function_block(
        function=error_unsupported,
        input_schema={"query_info": QueryInfo},
        output_schema={"response": str},
        queue=shared_queue
    )
    
    format_response_block = create_function_block(
        function=format_weather_response,
        input_schema={"weather_data": WeatherData},
        output_schema={"response": str},
        queue=shared_queue
    )
    
    # Print debug information about blocks
    print("BLOCK INFO:")
    print(f"Extract info block: {extract_info_block.name} ({extract_info_block.id})")
    print(f"Decision block: {decision_block.name} ({decision_block.id})")
    print(f"Fetch weather block: {fetch_weather_block.name} ({fetch_weather_block.id})")
    
    # Add blocks to workflow
    workflow.add_block(extract_info_block)
    workflow.add_block(decision_block)
    workflow.add_block(fetch_weather_block)
    workflow.add_block(ask_clarification_block)
    workflow.add_block(error_block)
    workflow.add_block(format_response_block)
    
    # Set start and end blocks
    workflow.set_start_block(extract_info_block)
    workflow.set_end_block(format_response_block)
    
    # Connect blocks
    print("\nCONNECTING BLOCKS:")
    print(f"Connecting extract_info_block head 'query_info' to decision_block slot 'query_info'")
    extract_info_block.connect_head_to_slot("query_info", decision_block, "query_info")
    
    # Connect decision routes
    print(f"Connecting decision_block route FETCH_WEATHER to fetch_weather_block slot 'query_info'")
    decision_block.connect_route(QueryAction.FETCH_WEATHER, fetch_weather_block, "query_info")
    
    print(f"Connecting decision_block route ASK_FOR_CLARIFICATION to ask_clarification_block slot 'query_info'")
    decision_block.connect_route(QueryAction.ASK_FOR_CLARIFICATION, ask_clarification_block, "query_info")
    
    print(f"Connecting decision_block route ERROR_UNSUPPORTED to error_block slot 'query_info'")
    decision_block.connect_route(QueryAction.ERROR_UNSUPPORTED, error_block, "query_info")
    
    # Connect to format response
    print(f"Connecting fetch_weather_block head 'weather_data' to format_response_block slot 'weather_data'")
    fetch_weather_block.connect_head_to_slot("weather_data", format_response_block, "weather_data")
    
    return workflow


def main():
    """Execute the weather query workflow with sample or provided queries"""
    # Create the workflow
    workflow = create_weather_workflow()
    
    # Add more logging to debug execution
    print(f"\nDEBUG OUTPUT:")
    print(f"Start block: {workflow.start_block.name}")
    print(f"End block: {workflow.end_block.name if workflow.end_block else 'None'}")
    
    # Log all blocks in the workflow
    print("\nAll blocks in workflow:")
    for block in workflow.blocks:
        print(f"- {block.name} ({block.id})")
    
    # Test queries
    test_queries = [
        "What's the weather like in Tokyo tomorrow?",
        "Will it rain in London this weekend?",
        "How hot will it be in Paris today?",
        "What's the weather like in unknown city?",
        "Will there be an earthquake in Tokyo tomorrow?",  # Unsupported query type
    ]
    
    # Get user query if provided, otherwise use test queries
    if len(sys.argv) > 1:
        test_queries = [" ".join(sys.argv[1:])]
    
    print("\nWeather Query Workflow Example")
    print("-----------------------------")
    
    for i, query_text in enumerate(test_queries):
        print(f"\n\nQUERY {i+1}: {query_text}")
        print("-" * (len(query_text) + 9))
        
        # Create query object
        query = WeatherQuery(raw_query=query_text)
        
        # Reset and execute workflow
        workflow.reset()
        
        # Execute workflow directly with input
        result = workflow.execute(query)
        
        # Find output blocks
        format_response_block = next((b for b in workflow.blocks if b.name == "format_weather_response"), None)
        ask_clarification_block = next((b for b in workflow.blocks if b.name == "ask_for_clarification"), None)
        error_block = next((b for b in workflow.blocks if b.name == "error_unsupported"), None)
        
        # Get final response from whichever block executed
        response = None
        if format_response_block and hasattr(format_response_block, 'heads') and format_response_block.heads["response"].data is not None:
            response = format_response_block.heads["response"].data
            print(f"RESULT: {response}")
        elif ask_clarification_block and hasattr(ask_clarification_block, 'heads') and ask_clarification_block.heads["response"].data is not None:
            response = ask_clarification_block.heads["response"].data
            print(f"CLARIFICATION NEEDED: {response}")
        elif error_block and hasattr(error_block, 'heads') and error_block.heads["response"].data is not None:
            response = error_block.heads["response"].data
            print(f"ERROR: {response}")
        else:
            print("No response generated")
    
    # Visualize the workflow
    try:
        workflow.visualize("weather_workflow", view=True)
        print("\nWorkflow visualization saved to weather_workflow.pdf")
    except Exception as e:
        print(f"\nCould not generate workflow visualization: {e}")
        print("Make sure graphviz is installed.")


if __name__ == "__main__":
    main()