import os
from pprint import pprint

from dotenv import load_dotenv
from notion_client import Client

NOTION_PRODUCTION_DATABASE_ID_TASKS: str = "ed8ba37a719a47d7a796c2d373c794b9"
NOTION_PRODUCTION_DATABASE_ID_PROJECTS: str = "918affd4ce0d4b8eb7604d972fd24826"

if __name__ == "__main__":
    load_dotenv(override=True)
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    response = notion.databases.retrieve(database_id=NOTION_PRODUCTION_DATABASE_ID_TASKS)
    pprint(response)
