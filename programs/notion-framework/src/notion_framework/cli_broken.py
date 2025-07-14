"""Command-line interface for the Notion Framework."""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()


def get_notion_token() -> str:
    """Get Notion API token from environment or prompt."""
    token = os.getenv("NOTION_TOKEN")
    if not token:
        token = click.prompt("Notion API token", hide_input=True)
    return token


def parse_database_urls(urls: List[str]) -> List[str]:
    """Parse database URLs to extract database IDs."""
    database_ids = []
    
    for url in urls:
        if url.startswith("http"):
            # Extract database ID from URL
            if "/database/" in url:
                db_id = url.split("/database/")[-1].split("?")[0].split("#")[0]
            else:
                # Try to extract from general Notion URL
                parts = url.split("/")[-1].split("?")[0].split("#")[0]
                if len(parts) >= 32:
                    db_id = parts[-32:]
                else:
                    console.print(f"[red]Could not extract database ID from URL: {url}[/red]")
                    continue
        else:
            # Assume it's already a database ID
            db_id = url.replace("-", "")
        
        database_ids.append(db_id)
    
    return database_ids


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool):
    """Notion Framework CLI - Generate typed tools from Notion databases."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    console.print(Panel.fit(
        "[bold blue]Notion Framework[/bold blue]\n"
        "Generate typed tools from Notion database schemas",
        style="blue"
    ))


@cli.command()
@click.option("--token", "-t", help="Notion API token (or set NOTION_TOKEN env var)")
@click.option("--output", "-o", default="./generated", help="Output directory for generated code")
@click.argument("databases", nargs=-1, required=True)
def generate(token: Optional[str], output: str, databases: tuple):
    """Generate tools from Notion databases.
    
    DATABASES: List of database URLs or IDs
    """
    
    async def _generate():
        from llmgine.bus.bus import MessageBus

        from .integration.framework import NotionFramework
        
        # Get token
        notion_token = token or get_notion_token()
        
        # Parse database IDs
        database_ids = parse_database_urls(list(databases))
        
        if not database_ids:
            console.print("[red]No valid database IDs provided[/red]")
            sys.exit(1)
        
        console.print(f"[green]Analyzing {len(database_ids)} databases...[/green]")
        
        # Initialize message bus and session
        message_bus = MessageBus()
        await message_bus.start()
        
        try:
            async with message_bus.create_session() as session:
                # Initialize framework
                framework = NotionFramework(session, notion_token)
                
                try:
                    # Analyze workspace
                    workspace = await framework.analyze_workspace(database_ids)
                    
                    # Display workspace info
                    _display_workspace_info(workspace)
                    
                    # Generate code
                    output_path = Path(output)
                    generated_files = await framework.generate_code(output_path)
                    
                    # Display results
                    _display_generation_results(generated_files, output_path)
                    
                except Exception as e:
                    console.print(f"[red]Generation failed: {e}[/red]")
                    logger.exception("Generation failed")
                    sys.exit(1)
                finally:
                    await framework.close()
                    
        finally:
            await message_bus.stop()
    
    asyncio.run(_generate())


@cli.command()
@click.option("--token", "-t", help="Notion API token")
@click.option("--query", "-q", help="Search query")
def search(token: Optional[str], query: Optional[str]):
    """Search for databases in your Notion workspace."""
    
    async def _search():
        from llmgine.bus.bus import MessageBus

        from .integration.framework import NotionFramework
        
        # Get token
        notion_token = token or get_notion_token()
        
        try:
            # Initialize message bus and session
            message_bus = MessageBus()
            await message_bus.start()
            
            try:
                async with message_bus.create_session() as session:
                    # Initialize framework
                    framework = NotionFramework(session, notion_token)
            
            # Search databases
            databases = await framework.search_databases(query)
            
            if not databases:
                console.print("[yellow]No databases found[/yellow]")
                return
            
            # Display results
            table = Table(title="Available Databases")
            table.add_column("Title", style="cyan")
            table.add_column("ID", style="green")
            table.add_column("URL", style="blue")
            table.add_column("Last Edited", style="yellow")
            
            for db in databases:
                table.add_row(
                    db["title"],
                    db["id"],
                    db["url"],
                    db.get("last_edited_time", "Unknown")
                )
            
            console.print(table)
            
            await framework.close()
            
        except Exception as e:
            console.print(f"[red]Search failed: {e}[/red]")
            logger.exception("Search failed")
            sys.exit(1)
    
    asyncio.run(_search())


@cli.command()
@click.option("--token", "-t", help="Notion API token")
@click.argument("databases", nargs=-1, required=True)
def analyze(token: Optional[str], databases: tuple):
    """Analyze database schemas without generating code.
    
    DATABASES: List of database URLs or IDs
    """
    
    async def _analyze():
        from llmgine.bus.bus import MessageBus

        from .integration.framework import NotionFramework
        
        # Get token
        notion_token = token or get_notion_token()
        
        # Parse database IDs
        database_ids = parse_database_urls(list(databases))
        
        if not database_ids:
            console.print("[red]No valid database IDs provided[/red]")
            sys.exit(1)
        
        try:
            # Initialize message bus and session
            message_bus = MessageBus()
            await message_bus.start()
            
            try:
                async with message_bus.create_session() as session:
                    # Initialize framework
                    framework = NotionFramework(session, notion_token)
            
            # Analyze workspace
            workspace = await framework.analyze_workspace(database_ids)
            
            # Display detailed analysis
            _display_detailed_analysis(workspace)
            
            await framework.close()
            
        except Exception as e:
            console.print(f"[red]Analysis failed: {e}[/red]")
            logger.exception("Analysis failed")
            sys.exit(1)
    
    asyncio.run(_analyze())


@cli.command()
@click.option("--token", "-t", help="Notion API token")
@click.option("--output", "-o", default="./generated", help="Output directory")
@click.argument("databases", nargs=-1, required=True)
def validate(token: Optional[str], output: str, databases: tuple):
    """Validate database schemas for code generation.
    
    DATABASES: List of database URLs or IDs
    """
    
    async def _validate():
        from llmgine.bus.bus import MessageBus

        from .integration.framework import NotionFramework
        from .schema.validator import SchemaValidator
        
        # Get token
        notion_token = token or get_notion_token()
        
        # Parse database IDs
        database_ids = parse_database_urls(list(databases))
        
        if not database_ids:
            console.print("[red]No valid database IDs provided[/red]")
            sys.exit(1)
        
        try:
            # Initialize message bus and session
            message_bus = MessageBus()
            await message_bus.start()
            
            try:
                async with message_bus.create_session() as session:
                    # Initialize framework
                    framework = NotionFramework(session, notion_token)
            
            # Analyze workspace
            workspace = await framework.analyze_workspace(database_ids)
            
            # Validate
            validator = SchemaValidator()
            issues = validator.validate_for_code_generation(workspace)
            
            if not issues:
                console.print("[green]✓ All schemas are valid for code generation[/green]")
            else:
                console.print(f"[red]✗ Found {len(issues)} validation issues:[/red]")
                for issue in issues:
                    console.print(f"  [red]•[/red] {issue}")
                sys.exit(1)
            
            await framework.close()
            
        except Exception as e:
            console.print(f"[red]Validation failed: {e}[/red]")
            logger.exception("Validation failed")
            sys.exit(1)
    
    asyncio.run(_validate())


def _display_workspace_info(workspace):
    """Display workspace information."""
    table = Table(title="Workspace Analysis")
    table.add_column("Database", style="cyan")
    table.add_column("Properties", justify="right", style="green")
    table.add_column("Editable", justify="right", style="yellow")
    table.add_column("Relations", justify="right", style="blue")
    
    for db in workspace.databases.values():
        table.add_row(
            db.title,
            str(len(db.properties)),
            str(len(db.editable_properties)),
            str(len(db.relation_properties))
        )
    
    console.print(table)
    
    if workspace.relationships:
        console.print(f"\n[blue]Found {len(workspace.relationships)} relationships between databases[/blue]")


def _display_detailed_analysis(workspace):
    """Display detailed workspace analysis."""
    for db in workspace.databases.values():
        panel = Panel.fit(
            f"[bold]{db.title}[/bold]\n"
            f"ID: {db.id}\n"
            f"Properties: {len(db.properties)}\n"
            f"Editable: {len(db.editable_properties)}\n"
            f"Required: {len(db.required_properties)}\n"
            f"Relations: {len(db.relation_properties)}",
            title=f"Database: {db.title}",
            style="blue"
        )
        console.print(panel)
        
        # Show properties
        if db.properties:
            prop_table = Table(title="Properties")
            prop_table.add_column("Name", style="cyan")
            prop_table.add_column("Type", style="green")
            prop_table.add_column("Required", justify="center", style="yellow")
            prop_table.add_column("Editable", justify="center", style="blue")
            
            for prop in db.properties.values():
                prop_table.add_row(
                    prop.name,
                    prop.type,
                    "✓" if prop.is_required else "✗",
                    "✓" if prop.is_editable else "✗"
                )
            
            console.print(prop_table)
        
        console.print()  # Add spacing


def _display_generation_results(generated_files, output_path):
    """Display code generation results."""
    console.print("\n[green]✓ Code generation completed successfully![/green]")
    console.print(f"Output directory: [blue]{output_path.absolute()}[/blue]")
    
    # Show generated files
    if generated_files["databases"]:
        console.print(f"\n[cyan]Generated {len(generated_files['databases'])} database classes:[/cyan]")
        for file_path in generated_files["databases"]:
            console.print(f"  • {file_path.name}")
    
    if generated_files["tools"]:
        console.print(f"\n[yellow]Generated {len(generated_files['tools'])} tool files:[/yellow]")
        for file_path in generated_files["tools"]:
            console.print(f"  • {file_path.name}")
    
    console.print("\n[green]Next steps:[/green]")
    console.print("1. Review the generated code")
    console.print("2. Import and register tools in your LLMgine application")
    console.print("3. Set up your Notion API token for runtime")


if __name__ == "__main__":
    cli()
