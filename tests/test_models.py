import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, User, Conversation, Message, get_database_url


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session"""
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


class TestUser:
    def test_user_creation(self, db_session):
        """Test user creation"""
        user = User(username="testuser", email="test@example.com", hashed_password="hashed")
        db_session.add(user)
        db_session.commit()

        retrieved = db_session.query(User).filter(User.username == "testuser").first()
        assert retrieved.username == "testuser"
        assert retrieved.email == "test@example.com"
        assert retrieved.hashed_password == "hashed"
        assert retrieved.is_active == True

    def test_user_unique_constraints(self, db_session):
        """Test unique constraints on username and email"""
        user1 = User(username="testuser", email="test@example.com", hashed_password="hashed")
        db_session.add(user1)
        db_session.commit()

        # Try to create user with same username
        user2 = User(username="testuser", email="test2@example.com", hashed_password="hashed")
        db_session.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

        db_session.rollback()

        # Try to create user with same email
        user3 = User(username="testuser2", email="test@example.com", hashed_password="hashed")
        db_session.add(user3)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestConversation:
    def test_conversation_creation(self, db_session):
        """Test conversation creation"""
        user = User(username="testuser", email="test@example.com", hashed_password="hashed")
        db_session.add(user)
        db_session.commit()

        conversation = Conversation(user_id=user.id, title="Test Conversation")
        db_session.add(conversation)
        db_session.commit()

        retrieved = db_session.query(Conversation).filter(Conversation.id == conversation.id).first()
        assert retrieved.user_id == user.id
        assert retrieved.title == "Test Conversation"

    def test_conversation_relationship(self, db_session):
        """Test conversation-user relationship"""
        user = User(username="testuser", email="test@example.com", hashed_password="hashed")
        db_session.add(user)
        db_session.commit()

        conversation = Conversation(user_id=user.id, title="Test Conversation")
        db_session.add(conversation)
        db_session.commit()

        # Test relationship from user to conversations
        assert len(user.conversations) == 1
        assert user.conversations[0].title == "Test Conversation"

        # Test relationship from conversation to user
        assert conversation.user.username == "testuser"


class TestMessage:
    def test_message_creation(self, db_session):
        """Test message creation"""
        user = User(username="testuser", email="test@example.com", hashed_password="hashed")
        db_session.add(user)
        db_session.commit()

        conversation = Conversation(user_id=user.id, title="Test Conversation")
        db_session.add(conversation)
        db_session.commit()

        message = Message(
            conversation_id=conversation.id,
            role="human",
            content="Test message"
        )
        db_session.add(message)
        db_session.commit()

        retrieved = db_session.query(Message).filter(Message.id == message.id).first()
        assert retrieved.conversation_id == conversation.id
        assert retrieved.role == "human"
        assert retrieved.content == "Test message"

    def test_message_relationship(self, db_session):
        """Test message-conversation relationship"""
        user = User(username="testuser", email="test@example.com", hashed_password="hashed")
        db_session.add(user)
        db_session.commit()

        conversation = Conversation(user_id=user.id, title="Test Conversation")
        db_session.add(conversation)
        db_session.commit()

        message = Message(
            conversation_id=conversation.id,
            role="human",
            content="Test message"
        )
        db_session.add(message)
        db_session.commit()

        # Test relationship from conversation to messages
        assert len(conversation.messages) == 1
        assert conversation.messages[0].content == "Test message"

        # Test relationship from message to conversation
        assert message.conversation.title == "Test Conversation"