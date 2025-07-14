# Notion Framework (Prototype)

⚠️ **This is a prototype implementation and not production-ready**

A tool generation framework for creating typed LLMgine tools from Notion database schemas. This framework analyzes Notion databases and automatically generates type-safe Python classes and LLMgine-compatible tools for CRUD operations.

## Overview

The Notion Framework bridges the gap between Notion databases and LLMgine applications by:

1. **Schema Analysis**: Introspects Notion database schemas and discovers relationships
2. **Type Generation**: Creates typed Python classes for each database with full property support  
3. **Tool Generation**: Generates comprehensive CRUD tools that integrate seamlessly with LLMgine
4. **Type Safety**: Provides compile-time type checking and runtime validation
5. **Filter Builders**: Type-safe query builders instead of raw JSON filters

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Notion API     │───▶│ Schema Analyzer  │───▶│ Code Generator  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Type Definitions │    │ Generated Tools │
                       └──────────────────┘    └─────────────────┘
                                │                        │
                                └────────────────────────┘
                                           │
                                           ▼
                                ┌─────────────────┐
                                │ LLMgine Engine  │
                                └─────────────────┘
```

## Features

### 🔍 Schema Analysis
- Discovers all database properties and their types
- Maps relationships between databases
- Validates schema for code generation compatibility
- Detects problematic property names and suggests fixes

### 🏗️ Code Generation
- **Database Classes**: Typed Python classes with getter/setter methods
- **CRUD Tools**: Create, read, update, delete operations for each database
- **Property Tools**: Specialized tools for select, checkbox, and relation properties
- **Filter Builders**: Type-safe query construction
- **Tool Registry**: Automatic LLMgine tool registration

### 🛡️ Type Safety
- Full support for 25+ Notion property types
- Pydantic validation for all generated classes
- TypeScript-style Literal types for select options
- Compile-time type checking with mypy

### 🔧 LLMgine Integration
- Proper MessageBus session handling
- Automatic tool registration
- Async-first design
- Error handling and logging

## Installation

This is a standalone package within the LLMgine repository:

```bash
# Navigate to the framework directory
cd programs/notion-framework

# Install with dependencies
uv sync

# Or install in development mode
uv pip install -e ".[dev]"
```

## Quick Start

### 1. Set up your Notion token

```bash
export NOTION_TOKEN="your_notion_integration_token"
```

### 2. Get your database IDs

Database IDs can be found in Notion URLs:
```
https://notion.so/workspace/DATABASE_ID?v=VIEW_ID
```

### 3. Generate tools

```bash
# CLI usage
uv run notion-framework generate DATABASE_ID_1 DATABASE_ID_2

# Or programmatically
python examples/basic_usage.py
```

### 4. Use generated tools

```python
from llmgine.bus.bus import MessageBus
from notion_framework import NotionFramework

async def main():
    message_bus = MessageBus()
    await message_bus.start()
    
    async with message_bus.create_session() as session:
        framework = NotionFramework(session, notion_token)
        
        # Analyze workspace
        workspace = await framework.analyze_workspace(database_ids)
        
        # Generate code
        generated_files = await framework.generate_code(Path("./generated"))
        
        # Load tools
        tools = await framework.load_and_register_tools("./generated/tools/registry.py")
```

## Generated Code Structure

```
generated/
├── __init__.py
├── databases/           # Typed database classes
│   ├── __init__.py
│   ├── projects.py      # Project database class
│   └── tasks.py         # Task database class
└── tools/              # LLMgine tools
    ├── __init__.py
    ├── projects_tools.py   # CRUD tools for projects
    ├── tasks_tools.py      # CRUD tools for tasks
    └── registry.py         # Tool registration
```

## Example Generated Database Class

```python
class Project(NotionPage):
    """Generated class for Project database."""
    
    # Typed properties
    name: str
    status: Optional[Literal["Not Started", "In Progress", "Done"]]
    priority: Optional[Literal["Low", "Medium", "High"]]
    assignee: List[str]  # User IDs
    due_date: Optional[datetime]
    
    # Property getters/setters
    def set_name(self, value: str) -> None:
        self._name_notion = NotionTitle(value)
    
    def get_name(self) -> str:
        return self._name_notion.plain_text if self._name_notion else ""
    
    # Filter helpers
    @classmethod
    def filter_by_status(cls, status: str) -> PropertyFilter:
        return PropertyFilter("Status", "select", {"equals": status})
    
    # CRUD operations
    async def create(self) -> str:
        """Create this project in Notion."""
        # Implementation...
    
    @classmethod
    async def list(cls, client: NotionClient, 
                   filter_condition: Optional[FilterCondition] = None,
                   sorts: Optional[List[SortCondition]] = None,
                   limit: int = 100) -> List["Project"]:
        """List projects with optional filtering and sorting."""
        # Implementation...
```

## Example Generated Tools

```python
# CRUD Tools
async def create_project(client: NotionClient, name: str, 
                        status: Optional[str] = None) -> str:
    """Create a new project."""

async def update_project(client: NotionClient, page_id: str, 
                        **kwargs) -> str:
    """Update an existing project."""

async def list_projects(client: NotionClient, limit: int = 10,
                       filter_by_status: Optional[str] = None) -> str:
    """List projects with optional filtering."""

# Property-specific tools  
async def set_project_status(client: NotionClient, page_id: str, 
                            status: str) -> str:
    """Set the status of a project."""
```

## Property Type Support

The framework supports all major Notion property types:

| Notion Type | Python Type | Description |
|-------------|-------------|-------------|
| `title` | `str` | Page titles |
| `rich_text` | `str` | Rich text content |
| `number` | `Union[int, float, None]` | Numeric values |
| `select` | `Optional[Literal[...]]` | Single selection |
| `multi_select` | `List[str]` | Multiple selections |
| `date` | `Optional[datetime]` | Date/datetime values |
| `checkbox` | `bool` | Boolean values |
| `relation` | `List[str]` | Related page IDs |
| `people` | `List[str]` | User IDs |
| `files` | `List[str]` | File URLs |
| `url` | `Optional[str]` | URL strings |
| `email` | `Optional[str]` | Email addresses |
| `phone_number` | `Optional[str]` | Phone numbers |
| `status` | `Optional[str]` | Status values |
| `created_time` | `datetime` | Creation timestamp |
| `last_edited_time` | `datetime` | Last edit timestamp |
| `created_by` | `str` | Creator user ID |
| `last_edited_by` | `str` | Last editor user ID |

## CLI Commands

```bash
# Generate tools for databases
uv run notion-framework generate [OPTIONS] DATABASE_IDS...

# Search for databases in workspace
uv run notion-framework search [OPTIONS]

# Analyze workspace schema
uv run notion-framework analyze [OPTIONS] DATABASE_IDS...

# Validate generated code
uv run notion-framework validate [OPTIONS] DATABASE_IDS...
```

## Limitations (Prototype Status)

This is a prototype with several known limitations:

### 🚧 Code Generation Issues
- Complex property types may not generate correctly
- Relationship mapping is basic and may miss edge cases
- Generated code may need manual refinement for production use
- Template system needs more robust error handling

### 🔧 LLMgine Integration
- Tool loading has some import resolution issues
- Session management could be more robust  
- Error handling in generated tools is basic
- Tool registration patterns may change with LLMgine updates

### 📋 Schema Analysis
- Limited validation of complex database structures
- Circular relationships not fully handled
- Property name normalization may cause conflicts
- Cross-database queries not implemented

### 🧪 Testing & Reliability
- Limited test coverage
- No integration tests with real Notion data
- Error handling needs improvement
- Performance not optimized for large databases

### 🎯 Missing Features
- No incremental code generation
- No schema migration support  
- Limited customization options
- No plugin system for custom property types

## Development

### Running Tests

```bash
pytest
pytest -sv --log-cli-level=0  # Verbose with logging
```

### Code Quality

```bash
ruff check src/           # Linting
ruff format src/          # Formatting  
mypy                      # Type checking
```

### Project Structure

```
src/notion_framework/
├── client/              # Notion API wrapper
├── types/               # Core type definitions
├── schema/              # Schema analysis
├── codegen/             # Code generation
├── integration/         # LLMgine integration
└── cli.py              # Command-line interface
```

## Contributing

This is a prototype for exploration and experimentation. If you encounter issues:

1. Check the generated code for obvious problems
2. Look at the validation warnings during analysis
3. Try with simpler database schemas first
4. Report issues with specific database structures that fail

## Roadmap

Future improvements for a production version might include:

- [ ] Robust error handling and recovery
- [ ] Incremental code generation
- [ ] Better relationship modeling
- [ ] Performance optimizations
- [ ] Comprehensive testing
- [ ] Plugin architecture
- [ ] Schema migration support
- [ ] Integration with LLMgine engines
- [ ] Web UI for code generation
- [ ] Advanced filtering and querying

## License

Part of the LLMgine project. See main repository license.

---

**⚠️ Remember: This is a prototype. Use for exploration and learning, not production applications.**