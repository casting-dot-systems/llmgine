"""Basic usage example for the Notion Framework."""

import asyncio
import os
from pathlib import Path

from llmgine.bus.bus import MessageBus
from llmgine.bus.session import BusSession
from notion_framework import NotionFramework
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

    # Create LLMgine message bus and session
    message_bus = MessageBus()
    await message_bus.start()

    try:
        async with message_bus.create_session() as session:
            # Initialize Notion Framework
            framework = NotionFramework(session, notion_token)

            try:
                print("🔍 Analyzing Notion workspace...")

                # Analyze workspace
                workspace = await framework.analyze_workspace(database_ids)

                print(f"✅ Found {workspace.database_count} databases:")
                for db in workspace.databases.values():
                    print(f"  • {db.title} ({len(db.properties)} properties)")

                print(f"🔗 Discovered {workspace.relationship_count} relationships")

                # Generate code
                print("\n🛠️  Generating code...")
                generated_files = await framework.generate_code(Path("./generated"))

                print(
                    f"✅ Generated {len(generated_files['databases'])} database classes"
                )
                print(f"✅ Generated {len(generated_files['tools'])} tool files")

                # Load and register tools (if code was generated)
                if generated_files["tools"]:
                    print("\n📦 Loading and registering tools...")
                    tools = await framework.load_and_register_tools(
                        "./generated/tools/registry.py"
                    )
                    print(f"✅ Registered {len(tools)} tools")

                    # Show available tools
                    print("\n🔧 Available tools:")
                    for tool in tools[:10]:  # Show first 10 tools
                        print(f"  • {tool.name}: {tool.description}")

                    if len(tools) > 10:
                        print(f"  ... and {len(tools) - 10} more")

                # Get workspace info
                workspace_info = framework.get_workspace_info()
                if workspace_info:
                    print(f"\n📊 Workspace Summary:")
                    print(f"  Databases: {workspace_info['database_count']}")
                    print(f"  Relationships: {workspace_info['relationship_count']}")
                    print(
                        f"  Total Properties: {sum(db['property_count'] for db in workspace_info['databases'])}"
                    )

            except Exception as e:
                print(f"❌ Error: {e}")

            finally:
                # Clean up
                await framework.close()
                print("\n🏁 Done!")

    finally:
        await message_bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
