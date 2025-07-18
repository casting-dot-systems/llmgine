"""Simplified NotionFramework class without LLMgine dependencies."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from .client.client import NotionClient
from .codegen.database_generator import DatabaseGenerator
from .codegen.template_engine import TemplateEngine
from .schema.analyzer import SchemaAnalyzer
from .types.database import WorkspaceSchema

logger = logging.getLogger(__name__)


class NotionFramework:
    """Simplified framework for generating typed CRUD functions from Notion databases."""
    
    def __init__(self, notion_token: str):
        """Initialize the framework with a Notion API token.
        
        Args:
            notion_token: Notion API token for authentication
        """
        self.notion_token = notion_token
        self.client = NotionClient(notion_token)
        self.analyzer = SchemaAnalyzer(self.client)
        self.template_engine = TemplateEngine()
        
    async def close(self):
        """Close the framework and clean up resources."""
        await self.client.close()
        
    async def analyze_workspace(self, database_ids: List[str]) -> WorkspaceSchema:
        """Analyze a workspace containing the specified databases.
        
        Args:
            database_ids: List of Notion database IDs to analyze
            
        Returns:
            Analyzed workspace with database schemas and relationships
        """
        logger.info(f"Analyzing workspace with {len(database_ids)} databases")
        
        # Analyze each database
        databases = {}
        for db_id in database_ids:
            try:
                db_schema = await self.analyzer.analyze_database(db_id)
                databases[db_id] = db_schema
                logger.info(f"Analyzed database: {db_schema.title}")
            except Exception as e:
                logger.error(f"Failed to analyze database {db_id}: {e}")
                raise
        
        # Create workspace
        workspace = WorkspaceSchema(databases=databases)
        
        # Analyze relationships
        workspace.discover_relationships()
        
        logger.info(f"Workspace analysis complete: {len(workspace.databases)} databases, {len(workspace.relationships)} relationships")
        
        # Store workspace for code generation
        self._workspace = workspace
        
        return workspace
    
    async def generate_code(self, output_path: Path) -> Dict[str, Any]:
        """Generate code for the analyzed workspace.
        
        Args:
            output_path: Directory to output generated code
            
        Returns:
            Dictionary with information about generated files
        """
        if not hasattr(self, '_workspace'):
            raise ValueError("Must analyze workspace before generating code")
        
        workspace = self._workspace
        
        logger.info(f"Generating code to {output_path}")
        
        # Ensure output directory exists
        output_path.mkdir(parents=True, exist_ok=True)
        
        generated_files = {
            "databases": [],
            "crud_functions": [],
            "types": []
        }
        
        # Generate database classes
        db_generator = DatabaseGenerator(self.template_engine)
        
        for db_id, database in workspace.databases.items():
            try:
                # Generate database class
                db_file = db_generator.generate_database_file(
                    database, output_path / "databases"
                )
                generated_files["databases"].append(db_file)
                
                # Generate CRUD functions
                crud_file = db_generator.generate_crud_functions(
                    database, output_path / "crud"
                )
                generated_files["crud_functions"].append(crud_file)
                
                logger.info(f"Generated code for database: {database.title}")
                
            except Exception as e:
                logger.error(f"Failed to generate code for database {database.title}: {e}")
                raise
        
        # Generate types file
        types_file = await self._generate_types_file(workspace, output_path)
        generated_files["types"].append(types_file)
        
        # Generate __init__.py files
        await self._generate_init_files(output_path)
        
        logger.info(f"Code generation complete: {len(generated_files['databases'])} database classes, {len(generated_files['crud_functions'])} CRUD function files")
        
        return generated_files
    
    async def _generate_types_file(self, workspace: WorkspaceSchema, output_path: Path) -> Path:
        """Generate a types file with all database ID types and enums."""
        types_content = '"""Generated types for Notion databases."""\n\n'
        types_content += 'from typing import Literal, Union\n'
        types_content += 'from enum import Enum\n\n'
        
        # Generate ID types for each database
        for db_id, database in workspace.databases.items():
            class_name = self._normalize_class_name(database.title)
            types_content += f'class {class_name}ID(str):\n'
            types_content += f'    """Type for {database.title} database IDs."""\n'
            types_content += f'    pass\n\n'
        
        # Generate enum types for select properties
        for db_id, database in workspace.databases.items():
            for prop_name, prop in database.properties.items():
                if prop.type == 'select' and prop.select_options:
                    db_class_name = self._normalize_class_name(database.title)
                    prop_class_name = self._normalize_class_name(prop_name)
                    enum_name = f"{db_class_name}_{prop_class_name}"
                    types_content += f'class {enum_name}(str, Enum):\n'
                    types_content += f'    """Enum for {database.title} {prop_name} property."""\n'
                    for option in prop.select_options:
                        option_name = self._normalize_enum_value(option.get('name', ''))
                        option_value = option.get('name', '')
                        types_content += f'    {option_name} = "{option_value}"\n'
                    types_content += '\n'
        
        types_file = output_path / "types.py"
        types_file.write_text(types_content)
        
        return types_file
    
    async def _generate_init_files(self, output_path: Path):
        """Generate __init__.py files for the generated packages."""
        # Main __init__.py
        init_content = '"""Generated Notion database code."""\n'
        (output_path / "__init__.py").write_text(init_content)
        
        # Database __init__.py
        db_dir = output_path / "databases"
        db_dir.mkdir(exist_ok=True)
        (db_dir / "__init__.py").write_text('"""Generated database classes."""\n')
        
        # CRUD __init__.py
        crud_dir = output_path / "crud"
        crud_dir.mkdir(exist_ok=True)
        (crud_dir / "__init__.py").write_text('"""Generated CRUD functions."""\n')
    
    async def search_databases(self, query: str) -> List[Dict[str, Any]]:
        """Search for databases in the workspace.
        
        Args:
            query: Search query
            
        Returns:
            List of matching databases
        """
        try:
            # Use the search endpoint
            response = await self.client.search(query=query, filter={"property": "object", "value": "database"})
            
            databases = []
            for result in response.get("results", []):
                if result.get("object") == "database":
                    databases.append({
                        "id": result["id"],
                        "title": result.get("title", [{}])[0].get("plain_text", "Untitled"),
                        "url": result.get("url", ""),
                        "created_time": result.get("created_time", ""),
                        "last_edited_time": result.get("last_edited_time", "")
                    })
            
            return databases
            
        except Exception as e:
            logger.error(f"Database search failed: {e}")
            raise
    
    async def validate_database_access(self, database_id: str) -> Dict[str, Any]:
        """Validate access to a database.
        
        Args:
            database_id: Database ID to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Try to retrieve the database
            database = await self.client.get_database(database_id)
            
            # Check if we can query it
            query_response = await self.client.query_database(database_id, page_size=1)
            
            return {
                "valid": True,
                "title": database.get("title", [{}])[0].get("plain_text", "Untitled"),
                "properties": len(database.get("properties", {})),
                "can_query": True,
                "message": "Database access validated successfully"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "title": None,
                "properties": 0,
                "can_query": False,
                "message": f"Database access validation failed: {e}"
            }
    

    def _normalize_class_name(self, name: str) -> str:
        """Normalize a name to a valid Python class name."""
        import re
        # Remove/replace invalid characters
        normalized = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '').replace('-', ''))
        # Ensure it starts with a letter
        if normalized and normalized[0].isdigit():
            normalized = f'DB_{normalized}'
        return normalized or 'UnnamedClass'
    
    def _normalize_enum_value(self, name: str) -> str:
        """Normalize a name to a valid Python enum value."""
        import re
        # Convert to uppercase and replace invalid characters
        normalized = name.upper().replace(' ', '_').replace('-', '_')
        normalized = re.sub(r'[^A-Z0-9_]', '_', normalized)
        # Ensure it starts with a letter
        if normalized and normalized[0].isdigit():
            normalized = f'_{normalized}'
        return normalized or 'UNNAMED'
