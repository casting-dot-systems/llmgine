"""Command-line interface for the Notion Framework."""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
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
def cli():
    """Notion Framework CLI - Generate typed CRUD functions for Notion databases."""
    pass


@cli.command()
@click.option("--token", "-t", help="Notion API token")
@click.option("--output", "-o", default="./generated", help="Output directory")
@click.argument("databases", nargs=-1, required=True)
def generate(token: Optional[str], output: str, databases: tuple):
    """Generate typed database classes and CRUD functions from Notion databases.
    
    DATABASES: List of database URLs or IDs
    """
    
    async def _generate():
        from .framework import NotionFramework
        
        # Get token
        notion_token = token or get_notion_token()
        
        # Parse database IDs
        database_ids = parse_database_urls(list(databases))
        
        if not database_ids:
            console.print("[red]No valid database IDs provided[/red]")
            sys.exit(1)
        
        console.print(f"[green]Analyzing {len(database_ids)} databases...[/green]")
        
        # Initialize framework
        framework = NotionFramework(notion_token)
        
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
    
    asyncio.run(_generate())


@cli.command()
@click.option("--token", "-t", help="Notion API token")
@click.argument("databases", nargs=-1, required=True)
def analyze(token: Optional[str], databases: tuple):
    """Analyze Notion databases and show their structure."""
    
    async def _analyze():
        from .framework import NotionFramework
        
        # Get token
        notion_token = token or get_notion_token()
        
        # Parse database IDs
        database_ids = parse_database_urls(list(databases))
        
        if not database_ids:
            console.print("[red]No valid database IDs provided[/red]")
            sys.exit(1)
        
        console.print(f"[green]Analyzing {len(database_ids)} databases...[/green]")
        
        # Initialize framework
        framework = NotionFramework(notion_token)
        
        try:
            # Analyze workspace
            workspace = await framework.analyze_workspace(database_ids)
            
            # Display workspace info
            _display_workspace_info(workspace)
            
        except Exception as e:
            console.print(f"[red]Analysis failed: {e}[/red]")
            logger.exception("Analysis failed")
            sys.exit(1)
        finally:
            await framework.close()
    
    asyncio.run(_analyze())


def _display_workspace_info(workspace):
    """Display workspace analysis results."""
    console.print("\n[bold green]Workspace Analysis Results[/bold green]")
    
    # Create a table for database info
    table = Table(title="Databases")
    table.add_column("Title", style="cyan")
    table.add_column("Properties", justify="right", style="magenta")
    table.add_column("Relations", justify="right", style="green")
    table.add_column("Editable", justify="right", style="yellow")
    
    for db in workspace.databases.values():
        table.add_row(
            db.title,
            str(len(db.properties)),
            str(len(db.relation_properties)),
            str(len(db.editable_properties))
        )
    
    console.print(table)
    
    if workspace.relationships:
        console.print(f"\n[bold]Found {len(workspace.relationships)} relationships:[/bold]")
        for rel in workspace.relationships:
            source_db = workspace.get_database(rel.source_database_id)
            target_db = workspace.get_database(rel.target_database_id)
            console.print(f"  • {source_db.title}.{rel.source_property_name} → {target_db.title}")


def _display_generation_results(generated_files, output_path):
    """Display code generation results."""
    console.print("\n[bold green]Code Generation Complete![/bold green]")
    console.print(f"Output directory: {output_path}")
    
    if generated_files.get("databases"):
        console.print(f"Generated {len(generated_files['databases'])} database classes")
    
    if generated_files.get("crud_functions"):
        console.print(f"Generated {len(generated_files['crud_functions'])} CRUD function files")
    
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Review the generated code")
    console.print("2. Import and use the generated functions in your Python application")
    console.print("3. Customize the generated code as needed")


if __name__ == "__main__":
    cli()
