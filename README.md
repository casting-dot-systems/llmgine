# Get Demo Working

Install UV on your computer https://github.com/astral-sh/uv

Clone repo

Cd into repo

Checkout the "legacy-demo" branch. 

do uv sync

do uv pip install -e .

then create a .env file with openai and notion key


finally run uv run .\src\programs\function_chat.py
