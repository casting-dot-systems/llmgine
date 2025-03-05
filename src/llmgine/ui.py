from typing import Dict, Any, List, Optional, Callable
import threading
import queue
import time


class UserInterface:
    """Base class for user interfaces"""

    def __init__(self, message_bus=None):
        self.message_bus = message_bus
        self.input_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        self.display_callbacks: List[Callable[[Any, str], None]] = []

        # Set up event handlers if message bus is available
        if message_bus:
            self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up event handlers for the UI"""
        # Subscribe to display events
        self.message_bus.subscribe_to_event("ui.display", self._handle_display_event)

    def _handle_display_event(self, event_data):
        """Handle a display event"""
        content = event_data.get("content")
        display_type = event_data.get("type", "text")

        self.display(content, display_type)

    def add_input_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add a callback for user input"""
        self.input_callbacks.append(callback)

    def add_display_callback(self, callback: Callable[[Any, str], None]):
        """Add a callback for display updates"""
        self.display_callbacks.append(callback)

    def process_input(self, input_text: str, metadata: Optional[Dict[str, Any]] = None):
        """Process user input"""
        metadata = metadata or {}

        # Call input callbacks
        for callback in self.input_callbacks:
            try:
                callback(input_text, metadata)
            except Exception as e:
                print(f"Error in input callback: {e}")

        # Publish event if message bus is available
        if self.message_bus:
            self.message_bus.publish_event(
                "ui.input", {"input_text": input_text, "metadata": metadata}
            )

    def display(self, content: Any, display_type: str = "text"):
        """Display content to the user"""
        # Call display callbacks
        for callback in self.display_callbacks:
            try:
                callback(content, display_type)
            except Exception as e:
                print(f"Error in display callback: {e}")


class ConsoleUI(UserInterface):
    """Simple console-based user interface"""

    def __init__(self, message_bus=None):
        super().__init__(message_bus)

        # Add default display callback
        self.add_display_callback(self._console_display)

    def _console_display(self, content: Any, display_type: str):
        """Display content in the console"""
        if display_type == "text":
            print(f"\n[OUTPUT]: {content}\n")
        elif display_type == "error":
            print(f"\n[ERROR]: {content}\n")
        elif display_type == "json":
            import json

            print(f"\n[JSON]: {json.dumps(content, indent=2)}\n")
        else:
            print(f"\n[{display_type.upper()}]: {content}\n")

    def start_input_loop(self):
        """Start a loop to read user input"""
        print("Welcome to LLMgine! Type 'exit' to quit.")

        try:
            while True:
                try:
                    user_input = input("\n[INPUT]: ")

                    if user_input.lower() in ["exit", "quit"]:
                        print("Exiting...")
                        break

                    self.process_input(user_input)
                except KeyboardInterrupt:
                    print("\nInterrupted. Type 'exit' to quit.")
                except Exception as e:
                    print(f"Error processing input: {e}")
        except Exception as e:
            print(f"Error in input loop: {e}")


class AsyncUI(UserInterface):
    """Asynchronous user interface that runs in a separate thread"""

    def __init__(self, message_bus=None):
        super().__init__(message_bus)
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.running = False
        self.input_thread = None
        self.output_thread = None

    def start(self):
        """Start the UI threads"""
        if self.running:
            return

        self.running = True

        # Start input thread
        self.input_thread = threading.Thread(target=self._input_loop)
        self.input_thread.daemon = True
        self.input_thread.start()

        # Start output thread
        self.output_thread = threading.Thread(target=self._output_loop)
        self.output_thread.daemon = True
        self.output_thread.start()

    def stop(self):
        """Stop the UI threads"""
        self.running = False

        # Wait for threads to finish
        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=1.0)

        if self.output_thread and self.output_thread.is_alive():
            self.output_thread.join(timeout=1.0)

    def _input_loop(self):
        """Loop to process input from the input queue"""
        while self.running:
            try:
                input_data = self.input_queue.get(timeout=0.1)
                if input_data is None:
                    continue

                input_text, metadata = input_data
                self.process_input(input_text, metadata)

                self.input_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in input loop: {e}")

    def _output_loop(self):
        """Loop to process output to the output queue"""
        while self.running:
            try:
                output_data = self.output_queue.get(timeout=0.1)
                if output_data is None:
                    continue

                content, display_type = output_data

                # Call display callbacks
                for callback in self.display_callbacks:
                    try:
                        callback(content, display_type)
                    except Exception as e:
                        print(f"Error in display callback: {e}")

                self.output_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in output loop: {e}")

    def send_input(self, input_text: str, metadata: Optional[Dict[str, Any]] = None):
        """Send input to the input queue"""
        self.input_queue.put((input_text, metadata or {}))

    def display(self, content: Any, display_type: str = "text"):
        """Display content by adding it to the output queue"""
        self.output_queue.put((content, display_type))
