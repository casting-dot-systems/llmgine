from llmgine.prompts.prompts import get_prompt

prompt = get_prompt("prompts/factextraction_prompt.md")

print(prompt.format(document_context="test1", sentence="test23", context="test3"))


