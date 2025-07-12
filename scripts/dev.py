#!/usr/bin/env python3
"""
Development convenience script for LLMgine.
Provides common development tasks in a single command.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: Path | None = None) -> int:
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="LLMgine development tools")
    parser.add_argument(
        "command",
        choices=["test", "lint", "format", "typecheck", "check", "clean", "install", "demo"],
        help="Command to run",
    )
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues where possible")

    args = parser.parse_args()
    project_root = Path(__file__).parent.parent

    if args.command == "test":
        sys.exit(run_command(["pytest"], cwd=project_root))

    elif args.command == "lint":
        cmd = ["ruff", "check", "src/", "tests/", "programs/"]
        if args.fix:
            cmd.append("--fix")
        sys.exit(run_command(cmd, cwd=project_root))

    elif args.command == "format":
        sys.exit(run_command(["ruff", "format", "src/", "tests/", "programs/"], cwd=project_root))

    elif args.command == "typecheck":
        sys.exit(run_command(["mypy"], cwd=project_root))

    elif args.command == "check":
        # Run all checks
        commands = [
            (["ruff", "check", "src/", "tests/", "programs/"], "Linting"),
            (["ruff", "format", "--check", "src/", "tests/", "programs/"], "Format check"),
            (["mypy"], "Type checking"),
            (["pytest"], "Tests"),
        ]

        for cmd, description in commands:
            print(f"\n=== {description} ===")
            if run_command(cmd, cwd=project_root) != 0:
                print(f"❌ {description} failed")
                sys.exit(1)
            print(f"✅ {description} passed")

    elif args.command == "clean":
        # Clean build artifacts
        dirs_to_clean = [
            "build",
            "dist",
            "*.egg-info",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "__pycache__",
        ]
        for pattern in dirs_to_clean:
            run_command(["find", ".", "-name", pattern, "-type", "d", "-exec", "rm", "-rf", "{}", "+"], cwd=project_root)

    elif args.command == "install":
        sys.exit(run_command(["uv", "pip", "install", "-e", ".[dev]"], cwd=project_root))

    elif args.command == "demo":
        print("Available demos:")
        print("1. python -m llmgine.engines.single_pass_engine  # Pirate translator")
        print("2. python -m llmgine.engines.tool_chat_engine    # Tool-enabled chat")
        print("\nMake sure you have set your API keys in .env file!")


if __name__ == "__main__":
    main()