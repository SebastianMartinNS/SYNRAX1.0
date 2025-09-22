import pytest
from unittest.mock import patch, MagicMock
from src.agent_new2 import AIAgent
from src.config import Config


class TestAIAgent:
    """Test AIAgent class"""

    @patch('src.agent_new2.ChatOllama')
    @patch('src.agent_new2.RAGSystem')
    @patch('src.agent_new2.AgentMemory')
    def test_initialization_success(self, mock_memory, mock_rag, mock_llm):
        """Test successful initialization"""
        config = Config()
        agent = AIAgent(config=config)

        assert agent.config == config
        mock_memory.assert_called_once()
        mock_rag.assert_called_once()
        mock_llm.assert_called_once_with(
            base_url=config.ollama_host,
            model=config.ollama_model,
            temperature=0.7
        )

    @patch('src.agent_new2.ChatOllama', side_effect=Exception("Connection failed"))
    @patch('src.agent_new2.RAGSystem')
    @patch('src.agent_new2.AgentMemory')
    def test_initialization_llm_failure(self, mock_memory, mock_rag, mock_llm):
        """Test initialization when LLM fails"""
        config = Config()
        agent = AIAgent(config=config)

        assert agent.llm is None
        assert agent.conversation is None

    def test_query_without_llm(self):
        """Test query when LLM is not available"""
        with patch('src.agent_new2.ChatOllama', side_effect=Exception("Failed")):
            agent = AIAgent()
            response = agent.query("test question")

            assert "limited mode" in response["answer"]
            assert response["source_documents"] == []

    @patch('src.agent_new2.ChatOllama')
    def test_query_with_llm(self, mock_llm_class):
        """Test query with working LLM"""
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm
        mock_llm.invoke.return_value = "Test response"

        with patch('src.agent_new2.RAGSystem') as mock_rag_class:
            mock_rag = MagicMock()
            mock_rag_class.return_value = mock_rag
            mock_retriever = MagicMock()
            mock_retriever.get_relevant_documents.return_value = []
            mock_rag.get_retriever.return_value = mock_retriever

            agent = AIAgent()
            response = agent.query("test question")

            assert response["answer"] == "Test response"
            assert response["source_documents"] == []

    def test_clear_memory(self):
        """Test memory clearing"""
        with patch('src.agent_new2.ChatOllama', side_effect=Exception("Failed")):
            agent = AIAgent()
            agent.clear_memory()  # Should not raise exception

    def test_ingest_documents(self):
        """Test document ingestion"""
        with patch('src.agent_new2.RAGSystem') as mock_rag_class:
            mock_rag = MagicMock()
            mock_rag_class.return_value = mock_rag

            agent = AIAgent()
            documents = ["test doc"]
            agent.ingest_documents(documents)

            mock_rag.ingest_documents.assert_called_once_with(documents)