from src.agent_new2 import AIAgent
from src.config import Config

def main():
    # Load config and initialize agent
    config = Config()
    agent = AIAgent(config=config)

    # Example documents for ingestion
    documents = [
        "AI agents are software programs that can perceive their environment and take actions to achieve specific goals.",
        "RAG (Retrieval-Augmented Generation) is a technique that combines information retrieval with text generation.",
        "Vector databases are optimized for storing and searching high-dimensional vectors, commonly used in AI applications."
    ]

    # Ingest documents
    agent.ingest_documents(documents)

    # Example query
    question = "What is RAG and how is it used?"
    response = agent.query(question)
    print(f"\nQuestion: {question}")
    print(f"Answer: {response['answer']}\n")

if __name__ == "__main__":
    main()