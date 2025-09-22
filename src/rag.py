from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.vectorstores.chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)

class RAGSystem:
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """Initialize the RAG system with the specified embedding model.

        Heavy components are lazy-loaded to speed up application startup.
        """
        self.embedding_model = embedding_model
        self.embeddings: Optional[HuggingFaceEmbeddings] = None
        self.vectorstore: Optional[Chroma] = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=400,
            separators=["\n\n", "\n", " ", ""],
            length_function=len,
        )

    def _ensure_embeddings(self) -> None:
        if self.embeddings is None:
            try:
                logger.info("Initializing HuggingFace embeddings (lazy-load)...")
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=self.embedding_model,
                    cache_folder="./.cache/embeddings",
                )
            except Exception as e:
                logger.error(f"Error initializing embeddings: {str(e)}", exc_info=True)
                raise

    def ingest_documents(self, documents: List[str]) -> None:
        """Process and store documents in the vector store."""
        try:
            # Handle empty documents list
            if not documents:
                logger.warning("Empty documents list provided to ingest_documents")
                return

            texts = [Document(page_content=doc) for doc in documents]
            chunks = self.text_splitter.split_documents(texts)
            logger.info(f"Created {len(chunks)} text chunks from {len(documents)} documents")
            
            # If vectorstore exists, add to it, otherwise create new one
            self._ensure_embeddings()
            if self.vectorstore:
                self.vectorstore.add_documents(chunks)
                logger.info(f"Added {len(chunks)} chunks to existing vectorstore")
            else:
                self.vectorstore = Chroma.from_documents(
                    documents=chunks,
                    embedding=self.embeddings,
                    persist_directory="./.cache/chroma"
                )
                logger.info("Created new vectorstore and ingested documents")
            
        except Exception as e:
            logger.error(f"Error ingesting documents: {str(e)}", exc_info=True)
            raise

    def get_retriever(self):
        """Get the retriever interface for the vectorstore."""
        if not self.vectorstore:
            logger.error("Vectorstore not initialized")
            raise ValueError("Vectorstore not initialized. Ingest documents first.")
            
        return self.vectorstore.as_retriever(
            search_kwargs={
                "k": 5,  # Return top 5 most relevant documents for better coverage
                "fetch_k": 20,  # Fetch more documents initially for better selection
                "lambda_mult": 0.5  # Adjust relevance threshold
            }
        )
