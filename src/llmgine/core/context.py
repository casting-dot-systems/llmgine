from typing import Dict, Any, List, Optional, Set
import json
import os
import time


class MemoryBlock:
    """A unit of memory in the context"""

    def __init__(self, content: Any, metadata: Optional[Dict[str, Any]] = None):
        self.content = content
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0

    def access(self):
        """Mark the memory block as accessed"""
        self.last_accessed = time.time()
        self.access_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert the memory block to a dictionary"""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
        }


class ContextManager:
    """Manages context, memory, and variables for the application"""

    def __init__(self, database_path: Optional[str] = None, message_bus=None):
        self.variables: Dict[str, Any] = {}
        self.memory: Dict[str, MemoryBlock] = {}
        self.chat_history: List[Dict[str, Any]] = []
        self.database_path = database_path
        self.message_bus = message_bus

        # Load from database if available
        if database_path and os.path.exists(database_path):
            self.load_from_database()

    def set_variable(self, name: str, value: Any):
        """Set a variable in the context"""
        self.variables[name] = value

        # Emit event if message bus is available
        if self.message_bus:
            self.message_bus.publish_event(
                "context.variable_set", {"name": name, "value": value}
            )

        # Save to database if available
        if self.database_path:
            self.save_to_database()

    def get_variable(self, name: str, default=None) -> Any:
        """Get a variable from the context"""
        value = self.variables.get(name, default)

        # Emit event if message bus is available
        if self.message_bus:
            self.message_bus.publish_event(
                "context.variable_get", {"name": name, "value": value}
            )

        return value

    def delete_variable(self, name: str):
        """Delete a variable from the context"""
        if name in self.variables:
            del self.variables[name]

            # Emit event if message bus is available
            if self.message_bus:
                self.message_bus.publish_event(
                    "context.variable_deleted", {"name": name}
                )

            # Save to database if available
            if self.database_path:
                self.save_to_database()

    def list_variables(self) -> List[str]:
        """List all variables in the context"""
        return list(self.variables.keys())

    def store_memory(
        self, memory_id: str, content: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a memory block in the context"""
        if memory_id is None:
            memory_id = f"memory_{len(self.memory)}"

        self.memory[memory_id] = MemoryBlock(content, metadata)

        # Emit event if message bus is available
        if self.message_bus:
            self.message_bus.publish_event(
                "context.memory_stored",
                {"memory_id": memory_id, "content": content, "metadata": metadata},
            )

        # Save to database if available
        if self.database_path:
            self.save_to_database()

        return memory_id

    def retrieve_memory(self, memory_id: str) -> Optional[Any]:
        """Retrieve a memory block from the context"""
        if memory_id in self.memory:
            memory_block = self.memory[memory_id]
            memory_block.access()

            # Emit event if message bus is available
            if self.message_bus:
                self.message_bus.publish_event(
                    "context.memory_retrieved",
                    {"memory_id": memory_id, "content": memory_block.content},
                )

            return memory_block.content

        return None

    def delete_memory(self, memory_id: str):
        """Delete a memory block from the context"""
        if memory_id in self.memory:
            del self.memory[memory_id]

            # Emit event if message bus is available
            if self.message_bus:
                self.message_bus.publish_event(
                    "context.memory_deleted", {"memory_id": memory_id}
                )

            # Save to database if available
            if self.database_path:
                self.save_to_database()

    def search_memory(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for memory blocks matching the query (simple implementation)"""
        results = []

        for memory_id, memory_block in self.memory.items():
            # Simple string matching for now
            if (
                isinstance(memory_block.content, str)
                and query.lower() in memory_block.content.lower()
            ):
                results.append(
                    {
                        "memory_id": memory_id,
                        "content": memory_block.content,
                        "metadata": memory_block.metadata,
                        "relevance": 1.0,  # Simple relevance score
                    }
                )

        # Sort by relevance and limit
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]

    def add_chat_message(
        self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a message to the chat history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }

        self.chat_history.append(message)

        # Emit event if message bus is available
        if self.message_bus:
            self.message_bus.publish_event("context.chat_message_added", message)

        # Save to database if available
        if self.database_path:
            self.save_to_database()

    def get_chat_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get the chat history"""
        if limit is None:
            return self.chat_history

        return self.chat_history[-limit:]

    def clear_chat_history(self):
        """Clear the chat history"""
        self.chat_history = []

        # Emit event if message bus is available
        if self.message_bus:
            self.message_bus.publish_event("context.chat_history_cleared", {})

        # Save to database if available
        if self.database_path:
            self.save_to_database()

    def save_to_database(self):
        """Save the context to the database"""
        if not self.database_path:
            return

        # Convert memory blocks to dictionaries
        memory_dict = {
            memory_id: memory_block.to_dict()
            for memory_id, memory_block in self.memory.items()
        }

        data = {
            "variables": self.variables,
            "memory": memory_dict,
            "chat_history": self.chat_history,
        }

        with open(self.database_path, "w") as f:
            json.dump(data, f)

    def load_from_database(self):
        """Load the context from the database"""
        if not self.database_path or not os.path.exists(self.database_path):
            return

        try:
            with open(self.database_path, "r") as f:
                data = json.load(f)

                self.variables = data.get("variables", {})

                # Convert memory dictionaries back to MemoryBlock objects
                self.memory = {}
                for memory_id, memory_dict in data.get("memory", {}).items():
                    memory_block = MemoryBlock(
                        content=memory_dict["content"], metadata=memory_dict["metadata"]
                    )
                    memory_block.created_at = memory_dict["created_at"]
                    memory_block.last_accessed = memory_dict["last_accessed"]
                    memory_block.access_count = memory_dict["access_count"]
                    self.memory[memory_id] = memory_block

                self.chat_history = data.get("chat_history", [])
        except Exception as e:
            print(f"Error loading context from database: {e}")

    def reset(self):
        """Reset the context"""
        self.variables = {}
        self.memory = {}
        self.chat_history = []

        # Emit event if message bus is available
        if self.message_bus:
            self.message_bus.publish_event("context.reset", {})

        # Save to database if available
        if self.database_path:
            self.save_to_database()
