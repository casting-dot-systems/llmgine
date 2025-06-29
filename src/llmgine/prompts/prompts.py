import os
from dataclasses import dataclass
from pathlib import Path
import string

# Helper dictionary for safe formatting
class SafeFormatterDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"

@dataclass
class Prompt:
    """Represents a prompt template that can be formatted."""
    template: str

    def format(self, **kwargs) -> str:
        """
        Formats the prompt template using the provided keyword arguments.
        If a key in the template is not found in kwargs, it leaves the placeholder unchanged.

        Args:
            **kwargs: The variables to substitute into the template.

        Returns:
            The formatted prompt string.
        """
        return self.template.format_map(SafeFormatterDict(**kwargs))

def get_prompt(file_path: str | Path) -> Prompt:
    """
    Reads a markdown prompt template from a file and returns a Prompt object.

    Args:
        file_path: The path to the markdown file containing the prompt template.

    Returns:
        A Prompt object initialized with the file content.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there is an error reading the file.
        ValueError: If the file extension is not .md
    """
    try:
        path = Path(file_path)
        if path.suffix.lower() != '.md':
            raise ValueError(f"Prompt file must be a markdown file (.md), got {path.suffix}")
        content = path.read_text(encoding='utf-8')
        return Prompt(template=content)
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {file_path}")
        raise
    except IOError as e:
        print(f"Error reading prompt file at {file_path}: {e}")
        raise

# New function to dump prompt to file
def dump_prompt(prompt: Prompt, file_path: str | Path):
    """
    Writes the prompt template content to a markdown file.

    Args:
        prompt: The Prompt object containing the template.
        file_path: The path to the markdown file where the template should be saved.

    Raises:
        IOError: If there is an error writing the file.
        OSError: If intermediate directories cannot be created.
        ValueError: If the file extension is not .md
    """
    try:
        path = Path(file_path)
        if path.suffix.lower() != '.md':
            raise ValueError(f"Prompt file must be a markdown file (.md), got {path.suffix}")
        # Ensure the directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(prompt.template, encoding='utf-8')
        print(f"Prompt successfully dumped to {path}")
    except (IOError, OSError) as e:
        print(f"Error dumping prompt to file at {file_path}: {e}")
        raise

# Example Usage (optional - can be removed or kept for testing):
if __name__ == "__main__":
    # Define the dummy file path (inside a 'prompts' subdirectory)
    # Ensures it doesn't clutter the root if run directly
    dummy_dir = Path("prompts")
    dummy_file = dummy_dir / "dummy_prompt.md"  # Changed to .md extension

    # Create a Prompt object with the template
    example_template = "Hello, {name}! Today is {day}. Feeling {mood}?"
    prompt_to_save = Prompt(template=example_template)

    try:
        # Use dump_prompt to write the template to the file
        dump_prompt(prompt_to_save, dummy_file)

        # Get the prompt back (optional, just to show get_prompt works)
        prompt_obj = get_prompt(dummy_file)
        print(f"Loaded prompt template: '{prompt_obj.template}'")

        # Format the prompt with a missing key ('mood' is missing)
        formatted_prompt = prompt_obj.format(name="World", day="Tuesday")
        print(f"Formatted prompt (with missing key): '{formatted_prompt}'")

        # Format the prompt with all keys
        formatted_prompt_full = prompt_obj.format(name="Universe", day="Wednesday", mood="great")
        print(f"Formatted prompt (full): '{formatted_prompt_full}'")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pass
