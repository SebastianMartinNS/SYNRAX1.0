import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.models import Base, User

# Set environment for registration before importing app
os.environ["ALLOW_USER_REGISTRATION"] = "true"

from web_new import app, get_password_hash, get_db

client = TestClient(app)

# Create test database with StaticPool for thread safety
engine = create_engine(
    "sqlite:///:memory:",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency for testing
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def test_register_user():
    response = client.post("/register", json={"username": "testuser", "email": "test@example.com", "password": "testpass"})
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

def test_login():
    # Register first
    response = client.post("/register", json={"username": "testlogin", "email": "testlogin@example.com", "password": "testpass"})
    assert response.status_code == 200
    response = client.post("/login", json={"username": "testlogin", "password": "testpass"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_query_unauthorized():
    response = client.post("/query", json={"question": "test"})
    assert response.status_code == 401

# Add more tests for upload, etc.