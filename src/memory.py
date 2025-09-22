from typing import List, Dict, Any
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class AgentMemory(ConversationBufferMemory):
    def __init__(self):
        super().__init__(
            return_messages=True,
            output_key="answer",
            input_key="question",
            memory_key="chat_history"
        )
        self._messages: List[BaseMessage] = []

    def add_message(self, message: str, is_human: bool = True) -> None:
        """Add a message to the memory."""
        msg = HumanMessage(content=message) if is_human else AIMessage(content=message)
        self._messages.append(msg)

    def get_messages(self) -> List[BaseMessage]:
        """Get all messages in memory."""
        return self._messages

    def clear(self) -> None:
        """Clear all messages from memory."""
        self._messages = []
        super().clear()

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load the memory variables."""
        return {
            "chat_history": self._messages
        }
