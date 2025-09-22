from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
from src.rag import RAGSystem
from src.memory import AgentMemory
from src.config import Config
from src.knowledge import KnowledgeSynthesizer
import logging
import os

logger = logging.getLogger(__name__)

class AIAgent:
    def __init__(self, config: Config = None):
        """Initialize the AI agent with modular components."""
        try:
            self.config = config or Config()
            self.memory = AgentMemory()
            self.rag = RAGSystem()
            try:
                self.llm = ChatOllama(
                    base_url=self.config.ollama_host,
                    model=self.config.ollama_model,
                    temperature=0.7
                )
                logger.info(f"Successfully initialized Ollama LLM: {self.config.ollama_model}")
            except Exception as e:
                logger.warning(f"Could not initialize Ollama LLM: {str(e)}")
                self.llm = None

            # Initialize the prompt template
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful AI assistant. Respond in a clear and concise manner."),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}")
            ])

            # Initialize the conversation chain
            self.conversation = None
            if self.llm:
                # Build a simple chain that reliably returns a string for tests/mocks
                self.conversation = (
                    RunnablePassthrough.assign(
                        chat_history=lambda x: self.memory.get_messages()
                    )
                    | self.prompt
                    | self.llm
                    | StrOutputParser()
                )
                logger.info("Conversation chain initialized successfully")
            else:
                logger.warning("Conversation chain not initialized due to missing LLM")
        except Exception as e:
            logger.error(f"Failed to initialize AI agent: {str(e)}", exc_info=True)
            raise

    def ingest_documents(self, documents: List[str]) -> None:
        """Process and store documents in the vector store via RAGSystem."""
        try:
            self.rag.ingest_documents(documents)
        except Exception as e:
            logger.error(f"Error ingesting documents: {str(e)}")
            raise

    def query(self, question: str) -> Dict[str, Any]:
        """Query the agent with a question."""
        if not self.llm:
            return {
                "answer": "I apologize, but I am currently running in limited mode without an LLM backend. Please ensure Ollama is installed and running.",
                "source_documents": []
            }
        
        try:
            # Add the user's question to memory
            self.memory.add_message(question, is_human=True)
            
            # Build prompt messages and invoke LLM directly for robustness with mocks
            messages = self.prompt.format_messages(
                chat_history=self.memory.get_messages(),
                question=question
            )
            raw_response = self.llm.invoke(messages)
            if hasattr(raw_response, "content"):
                response_text = raw_response.content
            else:
                response_text = str(raw_response)
            
            # Add the response to memory
            self.memory.add_message(response_text, is_human=False)
            
            # Get relevant documents from RAG system
            try:
                retriever = self.rag.get_retriever()
                source_documents = retriever.get_relevant_documents(question)
            except Exception as e:
                logger.warning(f"Error retrieving documents: {str(e)}")
                source_documents = []
            
            return {
                "answer": response_text,
                "source_documents": source_documents
            }
        except Exception as e:
            error_msg = f"I apologize, but I encountered an error: {str(e)}"
            logger.error(f"Error processing query: {str(e)}")
            return {
                "answer": error_msg,
                "source_documents": []
            }

    def clear_memory(self) -> None:
        """Clear the conversation memory."""
        try:
            self.memory.clear()
            logger.info("Conversation memory cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing memory: {str(e)}")
            raise

    def generate_security_report(self) -> Dict[str, Any]:
        """Generate a knowledge and security report for the project."""
        try:
            root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            synthesizer = KnowledgeSynthesizer(root_path)
            return synthesizer.generate_report()
        except Exception as e:
            logger.error(f"Error generating security report: {str(e)}")
            raise