import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.models import Base, User

# Set environment for registration before importing app
os.environ["ALLOW_USER_REGISTRATION"] = "true"

from web_new import app, get_db
from passlib.context import CryptContext

# Create test database with StaticPool for thread safety
engine = create_engine(
    "sqlite:///:memory:",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture(scope="function")
def test_user():
    """Create a test user"""
    db = TestingSessionLocal()
    hashed_password = pwd_context.hash("testpass")
    user = User(username="testuser", email="test@example.com", hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


class TestAuthAPI:
    def test_register_user(self):
        """Test user registration"""
        response = client.post("/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert data["disabled"] == False

    def test_register_duplicate_username(self):
        """Test registration with duplicate username"""
        # First registration
        client.post("/register", json={
            "username": "dupuser",
            "email": "dup@example.com",
            "password": "pass123"
        })

        # Duplicate username
        response = client.post("/register", json={
            "username": "dupuser",
            "email": "dup2@example.com",
            "password": "pass123"
        })
        assert response.status_code == 400

    def test_login_success(self):
        """Test successful login"""
        # Register user first
        client.post("/register", json={
            "username": "loginuser",
            "email": "login@example.com",
            "password": "loginpass"
        })

        # Login
        response = client.post("/login", json={
            "username": "loginuser",
            "password": "loginpass"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_failure(self):
        """Test login with wrong password"""
        response = client.post("/login", json={
            "username": "nonexistent",
            "password": "wrongpass"
        })
        assert response.status_code == 401


class TestProtectedAPI:
    def test_get_conversations_unauthorized(self):
        """Test accessing protected endpoint without auth"""
        response = client.get("/conversations")
        assert response.status_code == 401

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data


class TestConversationsAPI:
    def get_auth_token(self):
        """Helper to get auth token"""
        # Register and login
        client.post("/register", json={
            "username": "convuser",
            "email": "conv@example.com",
            "password": "convpass"
        })

        response = client.post("/login", json={
            "username": "convuser",
            "password": "convpass"
        })
        return response.json()["access_token"]

    def test_get_conversations_empty(self):
        """Test getting conversations when none exist"""
        token = self.get_auth_token()
        response = client.get("/conversations", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["conversations"] == []

    def test_query_creates_conversation(self):
        """Test that querying creates a conversation"""
        token = self.get_auth_token()

        # Query should succeed even without Ollama (graceful degradation)
        response = client.post("/query",
            json={"question": "Test question"},
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should return 200 with limited mode message
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "conversation_id" in data

        # Check conversations were created
        response = client.get("/conversations", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) >= 1