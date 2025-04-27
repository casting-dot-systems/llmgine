from llmgine.llm.engine import Engine
from llmgine.llm.models import Model


class SinglePassEngine(Engine):
    def __init__(self, model: Model):
        self.model = model

    def process(
        self, message: str, max_tokens: int = 5068, temperature: float = 0.7
    ) -> str:
        return self.model.generate(message, max_tokens, temperature).text
