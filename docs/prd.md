# llmgine Product Requirements Document (PRD)

## Goals and Background Context

### Goals

- Create a resilient, production-grade application library for building LLM applications.
- Provide a stable "runtime spine" that handles essential services like observability, component communication, and tool management.
- Enable a plug-and-play architecture where LLM frameworks and services can be treated as modular adapters.
- Ensure the developer experience is paramount, enabling startup teams to move from concept to production with confidence.

### Background Context

Developers building LLM applications currently face a difficult choice: either build all the application scaffolding from scratch or get locked into a single, opinionated framework. This framework lock-in makes it difficult to adapt to new tools and technologies, and often leads to brittle applications that are hard to scale and maintain.

`llmgine` solves this by providing the durable application layer that is often missing. By offering a decoupled, event-driven architecture with first-class observability and unified data contracts, it allows developers to focus on their unique business logic while retaining the flexibility to use any LLM provider or framework on top. This project aims to deliver the MVP of this "runtime spine."

### Change Log

| Date       | Version | Description                | Author    |
| :--------- | :------ | :------------------------- | :-------- |
| 2025-07-23 | 1.0     | Initial PRD draft creation | John (PM) |

---

## Requirements

### Functional

1.  **FR1**: The **library** must provide a **session-based**, asynchronous `MessageBus` component for dispatching `Command` and `Event` objects.
2.  **FR2**: The **library** must define and use unified data contracts for all LLM interactions, including a standard `LLMRequest` and `LLMResponse`.
3.  **FR3**: The **library** must include a `ToolManager` that allows for registering developer-defined Python functions and making them available for LLM execution.
4.  **FR4**: The **library** must provide a basic, in-memory `ContextStore` to manage and retrieve conversation history for a given session.
5.  **FR5**: The **library** must provide a dedicated observability client capable of sending logs, metrics, and traces to a compatible backend.

### Non-Functional

1.  **NFR1**: The library's core components (Message Bus, Observability, Tool Manager, Context Store) must be architected in a modular, plug-and-play fashion, allowing developers to replace or extend them.
2.  **NFR2**: The observability system must be compatible with the OpenTelemetry protocol to ensure broad integration possibilities.
3.  **NFR3**: All core components of the **library** must have comprehensive unit and integration test coverage to be considered "production-grade".
4.  **NFR4**: The **library** must be easily **integrable** into a new or existing Python application via a simple `ApplicationBootstrap` process.
5.  **NFR5**: The library's core components should expose a clear public API, encouraging users to interact with its features without modifying the library's internal source code.

---

## Technical Assumptions

### Repository Structure: Monorepo

- **Decision**: The project will be structured as a **Monorepo**.
- **Rationale**: This aligns with your description of having separate `apps` (e.g., discord-bot, darcy-backend) and `libs` (e.g., database, observability) packages that all depend on the core `llmgine` library. It simplifies dependency management and encourages code sharing.

### Service Architecture: Modular, Event-Driven

- **Decision**: The architecture will be **Modular and Event-Driven**, centered around the message bus.
- **Rationale**: This is the core principle of `llmgine`. It ensures that all components are decoupled and that the library can be used to build complex applications with independent services, without enforcing a strict microservices or monolith pattern on the user.

### Testing Requirements: Unit + Integration

- **Decision**: The library must have **comprehensive unit and integration tests**.
- **Rationale**: This is a direct reflection of the goal for `llmgine` to be of "production quality" (NFR3). All core library components must be verifiable and robust.

### Additional Technical Assumptions and Requests

- The primary development language for the library will be **Python**.
- Any example API services built with the library (e.g., for an app template) will preferably use **FastAPI** due to its modern, async-native design.
- The project will use **`uv`** for dependency and environment management for performance and simplicity.

---

## Epic List

1.  **Epic 1: Core Library Foundation & Message Bus**: Establish the core library structure, define all unified data contracts (Command, Event, LLMRequest/Response), and implement the session-based asynchronous message bus.
2.  **Epic 2: Production-Grade Observability**: Develop the dedicated observability client and integrate it with the message bus to handle and export logs, metrics, and traces using the OpenTelemetry protocol.
3.  **Epic 3: LLM Interaction Modules**: Implement the standardized Tool Manager for registering and executing functions, and the basic in-memory Context Store for managing conversation history.

---

## Epic Details

### Epic 1: Core Library Foundation & Message Bus

**Epic Goal**: The goal of this epic is to establish the fundamental scaffolding for the `llmgine` library. This includes setting up the monorepo, defining the core data contracts that will be used across the entire system, and implementing the fully-tested, session-based asynchronous message bus. Upon completion, the library will have a stable foundation for other modules to be built upon.

---

#### **Story 1.1: Project Scaffolding & Core Data Contracts**

**As a** developer using `llmgine`,
**I want** a clean project structure and well-defined core data contracts,
**so that** I can easily understand and start building upon the library's foundation.

**Acceptance Criteria:**

1.  A monorepo structure is initialized and configured using `uv`.
2.  Python dataclasses for `Command`, `Event`, `LLMRequest`, and `LLMResponse` are created, fully typed, and reside in a `messages` or `contracts` module.
3.  A `pyproject.toml` is configured with the initial project metadata and core dependencies (like `pytest`).
4.  A basic unit testing framework is set up and a sample test passes.

---

#### **Story 1.2: Asynchronous Message Bus Implementation**

**As a** developer using `llmgine`,
**I want** a robust, asynchronous message bus,
**so that** I can decouple components and build event-driven workflows.

**Acceptance Criteria:**

1.  A `MessageBus` class is implemented as a singleton that can be started and stopped.
2.  The bus can register handlers for specific `Command` and `Event` types.
3.  The bus has an `execute(command)` method that routes a command to its single registered handler and returns a result.
4.  The bus has a `publish(event)` method that adds an event to an async queue for processing.
5.  The bus correctly processes events from the queue and dispatches them to all registered handlers.
6.  Comprehensive unit tests for registration, execution, and publishing are implemented and passing.

---

#### **Story 1.3: Bus Session Management**

**As a** developer using `llmgine`,
**I want** to manage handlers within a session,
**so that** I can group related operations and ensure automatic cleanup.

**Acceptance Criteria:**

1.  A `BusSession` class is implemented that can be used as an `async with` context manager.
2.  Command and event handlers can be registered specifically to a `BusSession` instance.
3.  When a `BusSession` context is exited, all of its specific handlers are automatically unregistered from the `MessageBus`.
4.  A `SessionStartEvent` is published when a session begins, and a `SessionEndEvent` is published when it ends.
5.  Unit tests for the complete session lifecycle (creation, handler registration, cleanup) are implemented and passing.

---

### Epic 2: Production-Grade Observability

**Epic Goal**: This epic builds directly on the foundation of the message bus. Its goal is to implement the dedicated, pluggable observability system, a core feature of `llmgine`'s production-ready promise. We will create a client and initial handlers to capture and export telemetry data (logs, metrics, traces) using the OpenTelemetry standard, making user applications observable from day one.

---

#### **Story 2.1: Observability Client & Base Handler**

**As a** developer using `llmgine`,
**I want** a simple observability client and a base handler structure,
**so that** I can begin capturing telemetry data from my application in a standardized way.

**Acceptance Criteria:**

1.  An `ObservabilityEventHandler` base class is defined, which can process `Event` objects from the message bus.
2.  The `ApplicationBootstrap` process is updated to allow for the registration of one or more observability handlers.
3.  When registered, observability handlers automatically subscribe to all events published on the message bus.
4.  Unit tests for the basic registration and event-forwarding mechanism are implemented and passing.

---

#### **Story 2.2: Console and File Log Handlers**

**As a** developer using `llmgine`,
**I want** built-in console and file-based observability handlers,
**so that** I can easily debug and inspect events during local development.

**Acceptance Criteria:**

1.  A `ConsoleEventHandler` is implemented that prints a formatted, human-readable summary of any event it receives to the console.
2.  A `FileEventHandler` is implemented that serializes the full data of any event it receives to a specified JSONL file.
3.  The log format for both handlers is structured and includes the event type, timestamp, and session ID.
4.  The handlers can be enabled or disabled individually via the `ApplicationBootstrap` configuration.
5.  Unit tests confirm that both handlers correctly process and output event data in the specified format.

---

#### **Story 2.3: OpenTelemetry (OTel) Handler Integration**

**As a** developer using `llmgine`,
**I want** an OpenTelemetry handler,
**so that** I can export my application's telemetry data to any OTel-compatible backend (like Jaeger or Datadog) for production monitoring.

**Acceptance Criteria:**

1.  An `OpenTelemetryEventHandler` is implemented that depends on the standard OpenTelemetry Python libraries.
2.  The handler correctly converts key `llmgine` `Event` objects (like `CommandStartedEvent`, `CommandResultEvent`) into OTel `Spans` or `LogRecords`.
3.  The handler is configured to export data via the standard OTel OTLP (OpenTelemetry Protocol) exporter.
4.  The `ApplicationBootstrap` allows for easy configuration of the OTel handler and its export endpoint URL.
5.  Integration tests (using an in-memory OTel collector) confirm that `llmgine` events are successfully exported as valid OTel data.

---

### Epic 3: LLM Interaction Modules

**Epic Goal**: This epic delivers the high-level, LLM-specific utility modules that make `llmgine` a powerful tool for building AI applications. Building upon the core bus and data contracts from Epic 1, we will implement the standardized Tool Manager for handling function calls and the basic in-memory Context Store for managing conversation history. Completing this epic will finalize the core feature set for the Minimum Viable Product (MVP).

---

#### **Story 3.1: Tool Registration and Schema Generation**

**As a** developer using `llmgine`,
**I want** to register a Python function as a tool and have its schema automatically generated,
**so that** I can easily make my application's functions available to an LLM.

**Acceptance Criteria:**

1.  A `ToolManager` class is implemented that can be initialized for a specific session.
2.  The `ToolManager` has a `register_tool` method that accepts a Python function.
3.  The manager automatically parses the function's signature and docstrings to create an OpenAI-compatible JSON schema.
4.  A `get_tools` method returns a list of all registered tools in the correct schema format for use in an LLM call.
5.  Unit tests confirm that functions with various signatures (e.g., different argument types, required/optional arguments) are correctly parsed into valid schemas.

---

#### **Story 3.2: Tool Call Execution**

**As a** developer using `llmgine`,
**I want** the `ToolManager` to securely execute a tool call received from an LLM,
**so that** I can fulfill the LLM's request for action.

**Acceptance Criteria:**

1.  The `ToolManager` has an `execute_tool_call` method that accepts a `ToolCall` object (containing an `id`, `name`, and JSON string of `arguments`).
2.  The method correctly identifies the registered function by name.
3.  It safely parses the arguments and passes them to the function.
4.  It correctly handles both `sync` and `async` tool functions.
5.  It returns the result of the function call in a format that can be sent back to the LLM.
6.  A `ToolExecuteResultEvent` is published to the message bus after every execution attempt (both success and failure).
7.  Unit tests cover successful execution, argument parsing errors, and tool-not-found scenarios.

---

#### **Story 3.3: In-Memory Context Store**

**As a** developer using `llmgine`,
**I want** a basic in-memory context store,
**so that** I can easily maintain and retrieve the history of a conversation for multi-turn interactions.

**Acceptance Criteria:**

1.  An `InMemoryContextStore` class is implemented.
2.  It has an `add_message(session_id, message)` method that appends a message to a specific conversation's history.
3.  It has a `get_context(session_id)` method that retrieves the complete list of messages for a conversation.
4.  It has a `clear_context(session_id)` method to reset a conversation.
5.  A `ChatHistoryUpdatedEvent` is published to the message bus whenever a context is modified.
6.  Unit tests verify all public methods and the event publishing mechanism.

---

## Checklist Results Report

The `pm-checklist` was executed against this document.

- **Overall Status**: ✅ PASS
- **Summary**: The PRD is comprehensive, logically structured, and provides a clear and sufficient basis for the Architect to begin technical design. The MVP scope is well-defined, and the epics/stories are sequenced logically to deliver incremental value. The "User Experience" sections were correctly marked as Not Applicable.

---

## Next Steps

### Architect Prompt

"This Product Requirements Document (PRD) for the `llmgine` library is now complete and validated. Please review it thoroughly and create the detailed **Architecture Document**. Your design should adhere to the Technical Assumptions and provide a concrete implementation plan for the defined epics and stories."
