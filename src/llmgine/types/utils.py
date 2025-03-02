from typing import Any


class Queue:
    def __init__(self):
        self.queue = []

    def add(self, item: Any):
        self.queue.append(item)

    def get(self) -> Any:
        return self.queue.pop(0)

    def is_empty(self) -> bool:
        return len(self.queue) == 0
