from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from typing import Optional
import os

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conversations = relationship("Conversation", back_populates="user")

    def __init__(self, username: str, email: str, hashed_password: str, is_active: bool = True):
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
        self.is_active = is_active

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # 'human' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

# Database connection
def get_database_url():
    """Get database URL from environment or use SQLite for development"""
    return os.getenv("DATABASE_URL", "sqlite:///./ai_agent.db")

# Initialize a single Engine and SessionLocal per process (FastAPI best practice)
_DATABASE_URL = get_database_url()
_ENGINE = create_engine(
    _DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in _DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_ENGINE)

# Create tables at import time (idempotent); in migrations setups, replace with Alembic
Base.metadata.create_all(bind=_ENGINE)

def create_engine_and_session():
    """Backwards-compatible helper returning the global engine and session factory."""
    return _ENGINE, SessionLocal

# Dependency for FastAPI
def get_db():
    """Database dependency for FastAPI using the global SessionLocal."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()