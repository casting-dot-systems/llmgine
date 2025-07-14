"""Main integration framework for LLMgine."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from llmgine.bus.session import BusSession
from llmgine.llm.tools import Tool
from llmgine.llm.tools.tool_register import ToolRegister

from ..client.client import NotionClient, NotionClientConfig
from ..client.exceptions import NotionFrameworkError
from ..codegen.database_generator import DatabaseGenerator
from ..codegen.template_engine import TemplateEngine
from ..codegen.tool_generator import ToolGenerator
from ..schema.analyzer import SchemaAnalyzer
from ..schema.validator import SchemaValidator
from ..types.database import WorkspaceSchema
from .tool_registry import NotionToolRegistry

logger = logging.getLogger(__name__)


class NotionFramework:
    """Main framework class for integrating Notion with LLMgine."""
    
    def __init__(self, session: BusSession, notion_token: str):
        self.session = session
        self.tool_register = ToolRegister()
        
        # Initialize Notion client
        client_config = NotionClientConfig(auth=notion_token)
        self.notion_client = NotionClient(client_config)
        
        # Initialize components
        self.template_engine = TemplateEngine()
        self.database_generator = DatabaseGenerator(self.template_engine)
        self.tool_generator = ToolGenerator(self.template_engine)
        self.schema_analyzer = SchemaAnalyzer(self.notion_client)
        self.schema_validator = SchemaValidator()
        self.tool_registry = NotionToolRegistry()
        
        # State
        self.workspace_schema: Optional[WorkspaceSchema] = None
        self.generated_tools: List[Tool] = []
    
    async def analyze_workspace(self, database_ids: List[str]) -> WorkspaceSchema:
        """Analyze a workspace with the given database IDs."""
        logger.info(f"Analyzing workspace with {len(database_ids)} databases")
        
        try:
            workspace = await self.schema_analyzer.analyze_workspace(database_ids)
            
            # Validate the workspace
            validation_issues = self.schema_validator.validate_workspace_schema(workspace)
            if validation_issues:
                logger.warning(f"Workspace has {len(validation_issues)} validation issues:")
                for issue in validation_issues:
                    logger.warning(f"  - {issue}")
            
            # Validate for code generation
            codegen_issues = self.schema_validator.validate_for_code_generation(workspace)
            if codegen_issues:
                logger.warning(f"Workspace has {len(codegen_issues)} code generation issues:")
                for issue in codegen_issues:
                    logger.warning(f"  - {issue}")
            
            self.workspace_schema = workspace
            logger.info(f"Successfully analyzed workspace: {workspace.database_count} databases, {workspace.relationship_count} relationships")
            
            return workspace
            
        except Exception as e:
            logger.error(f"Failed to analyze workspace: {e}")
            raise NotionFrameworkError(f"Workspace analysis failed: {e}")
    
    async def generate_code(self, output_dir: Path) -> Dict[str, List[Path]]:
        """Generate database classes and tools."""
        if not self.workspace_schema:
            raise NotionFrameworkError("No workspace schema available. Run analyze_workspace() first.")
        
        logger.info(f"Generating code for {self.workspace_schema.database_count} databases")
        
        try:
            generated_files = {
                "databases": [],
                "tools": []
            }
            
            # Create output directories
            databases_dir = output_dir / "databases"
            tools_dir = output_dir / "tools"
            
            databases_dir.mkdir(parents=True, exist_ok=True)
            tools_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate database classes
            for database_id, schema in self.workspace_schema.databases.items():
                try:
                    # Generate database class
                    db_file = self.database_generator.generate_database_file(schema, databases_dir)
                    generated_files["databases"].append(db_file)
                    
                    # Generate tools
                    tools_file = self.tool_generator.generate_database_tools_file(schema, tools_dir)
                    generated_files["tools"].append(tools_file)
                    
                    logger.info(f"Generated code for database '{schema.title}'")
                    
                except Exception as e:
                    logger.warning(f"Skipped code generation for database '{schema.title}': {e}")
                    continue
            
            # Generate workspace-level files
            workspace_tools = self.tool_generator.generate_workspace_tools(self.workspace_schema, output_dir)
            generated_files["tools"].extend(workspace_tools)
            
            # Generate init files
            self._generate_init_files(output_dir, generated_files)
            
            logger.info(f"Code generation complete: {len(generated_files['databases'])} database files, {len(generated_files['tools'])} tool files")
            
            return generated_files
            
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise NotionFrameworkError(f"Code generation failed: {e}")
    
    async def load_and_register_tools(self, tools_module_path: str) -> List[Tool]:
        """Load generated tools and register them with LLMgine."""
        try:
            logger.info(f"Loading tools from {tools_module_path}")
            
            # Add the generated directory to Python path for relative imports
            import importlib.util
            import sys
            from pathlib import Path
            
            tools_path = Path(tools_module_path)
            generated_dir = tools_path.parent.parent  # Go up from tools/registry.py to generated/
            
            # Add to sys.path if not already there
            if str(generated_dir) not in sys.path:
                sys.path.insert(0, str(generated_dir))
            
            try:
                # Import as module from the generated package
                import importlib
                logger.info(f"Attempting to import tools.registry with sys.path: {sys.path[:3]}")
                tools_module = importlib.import_module("tools.registry")
                logger.info("Successfully imported tools.registry")
            except ImportError as e:
                logger.warning(f"Failed to import tools.registry: {e}, falling back to direct file loading")
                # Fallback to direct file loading
                spec = importlib.util.spec_from_file_location("generated_tools", tools_module_path)
                if not spec or not spec.loader:
                    raise NotionFrameworkError(f"Could not load tools module from {tools_module_path}")
                
                tools_module = importlib.util.module_from_spec(spec)
                sys.modules["generated_tools"] = tools_module
                spec.loader.exec_module(tools_module)
            
            # Get all tools
            all_tools = tools_module.get_all_tools()
            
            # Inject Notion client into tool functions
            tools_with_client = []
            for tool in all_tools:
                # Create a wrapper function that injects the client
                original_function = tool.function
                
                async def wrapped_function(*args, **kwargs):
                    # Inject client as first argument
                    return await original_function(self.notion_client, *args, **kwargs)
                
                # Create new tool with wrapped function
                new_tool = Tool(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.parameters,
                    function=wrapped_function,
                    is_async=tool.is_async
                )
                tools_with_client.append(new_tool)
            
            # Register tools with LLMgine session
            # Tools are command-like functions, so we register them with the session
            # The ToolRegister just converts functions to Tool objects
            logger.info(f"Registering {len(tools_with_client)} tools with session")
            # TODO: Implement proper tool registration pattern with LLMgine
            # For now, store tools for later use
            
            self.generated_tools = tools_with_client
            logger.info(f"Successfully loaded and registered {len(tools_with_client)} tools")
            
            return tools_with_client
            
        except Exception as e:
            logger.error(f"Failed to load and register tools: {e}")
            raise NotionFrameworkError(f"Tool loading failed: {e}")
    
    def register_custom_tool(self, tool: Tool) -> None:
        """Register a custom tool with the framework."""
        # Wrap the tool function to inject the Notion client
        original_function = tool.function
        
        async def wrapped_function(*args, **kwargs):
            return await original_function(self.notion_client, *args, **kwargs)
        
        wrapped_tool = Tool(
            name=tool.name,
            description=tool.description,
            parameters=tool.parameters,
            function=wrapped_function,
            is_async=tool.is_async
        )
        
        # Store tool for later use - tool registration handled by LLMgine engines
        self.generated_tools.append(wrapped_tool)
        
        logger.info(f"Registered custom tool: {tool.name}")
    
    def get_workspace_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current workspace."""
        if not self.workspace_schema:
            return None
        
        return {
            "database_count": self.workspace_schema.database_count,
            "relationship_count": self.workspace_schema.relationship_count,
            "databases": [
                {
                    "id": db.id,
                    "title": db.title,
                    "property_count": len(db.properties),
                    "editable_properties": len(db.editable_properties),
                    "relation_properties": len(db.relation_properties),
                }
                for db in self.workspace_schema.databases.values()
            ],
            "relationships": [
                {
                    "source_database": self.workspace_schema.get_database(rel.source_database_id).title,
                    "target_database": self.workspace_schema.get_database(rel.target_database_id).title,
                    "property": rel.source_property_name,
                    "bidirectional": rel.target_property_name is not None,
                }
                for rel in self.workspace_schema.relationships
            ]
        }
    
    def get_registered_tools(self) -> List[str]:
        """Get list of registered tool names."""
        return [tool.name for tool in self.generated_tools]
    
    async def search_databases(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for databases in the workspace."""
        try:
            return await self.schema_analyzer.search_databases(query)
        except Exception as e:
            logger.error(f"Database search failed: {e}")
            raise NotionFrameworkError(f"Database search failed: {e}")
    
    def _generate_init_files(self, output_dir: Path, generated_files: Dict[str, List[Path]]) -> None:
        """Generate __init__.py files for the generated packages."""
        try:
            # Main package __init__.py
            main_init = output_dir / "__init__.py"
            main_init.write_text('"""Generated Notion framework code."""\n', encoding="utf-8")
            
            # Databases package __init__.py
            databases_init = output_dir / "databases" / "__init__.py"
            databases_init.write_text('"""Generated database classes."""\n', encoding="utf-8")
            
            logger.info("Generated __init__.py files")
            
        except Exception as e:
            logger.warning(f"Failed to generate __init__.py files: {e}")
    
    async def close(self) -> None:
        """Close the framework and cleanup resources."""
        try:
            await self.notion_client.close()
            logger.info("NotionFramework closed successfully")
        except Exception as e:
            logger.warning(f"Error closing NotionFramework: {e}")
    
    async def __aenter__(self) -> "NotionFramework":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
    
    @classmethod
    async def create_and_analyze(
        cls,
        session: BusSession,
        notion_token: str,
        database_ids: List[str]
    ) -> "NotionFramework":
        """Factory method to create framework and analyze workspace in one step."""
        framework = cls(session, notion_token)
        await framework.analyze_workspace(database_ids)
        return framework
