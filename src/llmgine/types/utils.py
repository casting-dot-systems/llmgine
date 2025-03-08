from typing import Any, List, Optional


class Queue:
    """A simple queue implementation for workflow blocks"""
    
    def __init__(self):
        self.queue = []
        self._current_item = None

    def add(self, item: Any) -> None:
        """Add an item to the queue"""
        if item not in self.queue:
            self.queue.append(item)

    def get(self) -> Any:
        """Get the next item from the queue"""
        if not self.queue:
            return None
        
        self._current_item = self.queue.pop(0)
        return self._current_item

    def is_empty(self) -> bool:
        """Check if the queue is empty"""
        return len(self.queue) == 0
        
    def requeue(self, item: Optional[Any] = None) -> None:
        """
        Requeue an item at the end of the queue
        If no item is provided, requeues the current item
        """
        if item is not None:
            # Requeue specific item
            if item in self.queue:
                self.queue.remove(item)
            self.queue.append(item)
        elif self._current_item is not None:
            # Requeue current item
            self.queue.append(self._current_item)
            self._current_item = None
        
    def __len__(self) -> int:
        """Get the length of the queue"""
        return len(self.queue)
        
    def clear(self) -> None:
        """Clear the queue"""
        self.queue.clear()
        self._current_item = None
