"""Basic usage example for the Notion Framework."""

import asyncio
import os
from pathlib import Path

from notion_framework.framework import NotionFramework
from dotenv import load_dotenv

load_dotenv(override=True)


async def main():
    """Demonstrate basic usage of the Notion Framework."""

    # Get Notion token from environment
    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        print("Please set NOTION_TOKEN environment variable")
        return

    # Example database IDs (replace with your own)
    database_ids = [
        "918affd4ce0d4b8eb7604d972fd24826",
        "ed8ba37a719a47d7a796c2d373c794b9",
        "139594e5-2bd9-47af-93ca-bb72a35742d2",
        "55909df8-1f56-40c4-9327-bab99b4f97f5",
    ]

    # Initialize Notion Framework
    framework = NotionFramework(notion_token)

    try:
        print("🔍 Analyzing Notion workspace...")

        # Analyze workspace
        workspace = await framework.analyze_workspace(database_ids)

        print(f"✅ Found {len(workspace.databases)} databases:")
        for db in workspace.databases.values():
            print(f"  • {db.title} ({len(db.properties)} properties)")

        print(f"🔗 Discovered {len(workspace.relationships)} relationships")

        # Generate code
        print("\n🛠️  Generating code...")
        generated_files = await framework.generate_code(Path("./generated"))

        print(f"✅ Generated {len(generated_files['databases'])} database classes")
        print(
            f"✅ Generated {len(generated_files['crud_functions'])} CRUD function files"
        )

        # Show some example usage
        print("\n📖 Example usage:")
        print("```python")
        print("from notion_framework.client.client import NotionClient")
        print(
            "from generated.crud.your_database import create_your_database, read_your_database"
        )
        print("")
        print("# Initialize client")
        print("client = NotionClient(notion_token)")
        print("")
        print("# Create a new row")
        print(
            "page_id = await create_your_database(client, title='New Item', status='In Progress')"
        )
        print("")
        print("# Read the row")
        print("data = await read_your_database(client, page_id)")
        print("print(data)")
        print("```")

        # Show workspace summary
        print(f"\n📊 Workspace Summary:")
        print(f"  Databases: {len(workspace.databases)}")
        print(f"  Relationships: {len(workspace.relationships)}")
        total_properties = sum(len(db.properties) for db in workspace.databases.values())
        print(f"  Total Properties: {total_properties}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up
        await framework.close()
        print("\n🏁 Done!")


if __name__ == "__main__":
    asyncio.run(main())
