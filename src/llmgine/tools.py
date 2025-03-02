from typing import List, Callable, Dict
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
import inspect
import json
from loguru import logger
from pprint import pformat


# ====== Function Calling Decorator ======


def tool(
    funct_descript: str,
    param_descript: Dict[str, str],
    required_parameters: List[str] = None,
    enum_parameters: Dict[str, List[str]] = None,
    strict: bool = True,
    additional_properties: bool = False,
) -> Callable:
    def decorator(funct: Callable) -> Callable:
        class FunctionWrapper:
            def __init__(self):
                self.funct = funct
                self.function_description = funct_descript
                self.parameter_descriptions = param_descript
                self.enum_parameters = enum_parameters
                self.required_parameters = required_parameters
                self.strict = strict
                self.output = {
                    "type": "function",
                    "function": {
                        "name": funct.__name__,
                        "description": self.function_description,
                        "parameters": {
                            "type": "object",
                            "required": self.required_parameters or [],
                            "properties": {},
                            "additionalProperties": additional_properties,
                        },
                        "strict": strict,
                    },
                }
                self._inspect_parameters()

            parameter_map = {
                str: "string",
                int: "integer",
                float: "number",
                bool: "boolean",
            }

            def _inspect_parameters(self):
                """
                Inspect the function signature and create a schema for the parameters
                """
                signature = inspect.signature(self.funct)
                for name, param in signature.parameters.items():
                    param_info = {
                        "description": self.parameter_descriptions.get(name, ""),
                        "type": (
                            self.parameter_map[param.annotation]
                            if param.annotation in self.parameter_map
                            else "string"
                        ),
                    }
                    if self.enum_parameters:
                        if name in self.enum_parameters:
                            param_info["enum"] = self.enum_parameters[name]
                    self.output["function"]["parameters"]["properties"][name] = (
                        param_info
                    )
                    if self.strict:
                        # openai recommends to use strict, so this is the default and 99%
                        self.output["function"]["parameters"]["required"].append(name)
                    else:
                        # if not strict, required parameters are those specified in the function signature
                        if name in self.required_parameters:
                            continue
                        # if the parameter does not have a default value, it is required
                        if param.default == inspect.Parameter.empty:
                            if (
                                name
                                not in self.output["function"]["parameters"]["required"]
                            ):
                                self.output["function"]["parameters"][
                                    "required"
                                ].append(name)

            def __call__(self, *args, **kwargs):
                return self.funct(*args, **kwargs)

        return FunctionWrapper()

    return decorator


# ====== Tool Manager Class ======


class ToolManager:
    def __init__(
        self,
        tools: List[Callable],
        store_result: Callable,
        # subject: EngineSubject,
        confirm: bool = False,
    ):
        """
        Args:
            tools: List of functions to be used as tools
            store_result: Function to store the result of the tool call
        """
        self.tools = tools
        self.tools_schema = create_tools_schema(tools)
        self.tools_lookup = create_tools_lookup(tools)
        self.store_result = store_result
        # self.subject = subject
        self.confirm = confirm
        self.confirm_status = True
        logger.debug(f"Tool Manager initialized with {len(tools)} tools")
        logger.debug(f"Tools schema: {pformat(self.tools_schema)}")

    def execute_responses(self, calls: List[ChatCompletionMessageToolCall]):
        for call in calls:
            # self.subject.notify({
            #     "type": EngineObserverEventType.FUNCTION_CALL,
            #     "tool_call_id": call.id,
            #     "name": call.function.name,
            #     "parameters": json.loads(call.function.arguments)
            # })
            # self.subject.notify(
            #     {
            #         "type": EngineObserverEventType.STATUS_UPDATE,
            #         "message": f"Executing function {call.function.name}...",
            #     }
            # )
            # if self.confirm:
            #     self.confirm_status = self.subject.get_input(
            #         {
            #             "type": EngineObserverEventType.GET_CONFIRMATION,
            #             # "message": f"[bold]Function:[/bold] '{call.function.name}'\n"
            #             #            f"[bold]Parameters:[/bold] {(json.loads(call.function.arguments))}"
            #             "message": {
            #                 "function": call.function.name,
            #                 "parameters": json.loads(call.function.arguments),
            #             },
            #         }
            #     )
            if self.confirm_status:
                try:
                    result = execute_function(call, tools_lookup=self.tools_lookup)
                    logger.info(f"Successfully executed function {call.function.name}")
                except Exception as e:
                    result = f"Error executing function {call.function.name}: {e}"
                    logger.info(f"Error executing function {call.function.name}: {e}")
            else:
                logger.info(f"Function {call.function.name} execution cancelled")
                result = "Function execution cancelled by user"
            result = {
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.function.name,
                "content": str(result),
            }
            self.store_result(result)
            # self.subject.notify(
            #     {
            #         "type": EngineObserverEventType.FUNCTION_RESULT,
            #         "tool_call_id": call.id,
            #         "name": call.function.name,
            #         "content": result,
            #     }
            # )
            logger.info(f"Stored function call result: {result}")


# ====== Tool Manager Helper Functions ======


def create_tools_schema(functions: List[callable]) -> List[Dict]:
    tools = []
    for function in functions:
        tools.append(function.output)
    return tools


def create_tools_lookup(functions: List[callable]) -> Dict[str, callable]:
    tools_lookup = {}
    for function in functions:
        tools_lookup[function.funct.__name__] = function
    return tools_lookup


def parse_functions(tool_calls: List[ChatCompletionMessageToolCall]) -> List[callable]:
    functions = []
    if tool_calls:
        for tool in tool_calls:
            if tool.type == "function":
                functions.append(tool)
    else:
        raise ValueError("No tool calls found in response")
    return functions


def execute_function(function_object, tools_lookup: Dict[str, callable]):
    function = tools_lookup[function_object.function.name]
    kwargs = json.loads(function_object.function.arguments)
    for key, value in kwargs.items():
        if value == "":
            kwargs[key] = None
    result = function(**kwargs)
    return str(result)
