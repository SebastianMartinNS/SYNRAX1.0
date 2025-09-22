import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from sqlalchemy.pool import StaticPool

# Ensure registration is enabled during tests regardless of .env
os.environ['ALLOW_USER_REGISTRATION'] = 'true'

from web_new import app, get_db, get_password_hash
from src.models import Base, User


# Set up in-memory database for this test module
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _register_and_login(username: str = "secuser", email: str = "sec@example.com", password: str = "pass123") -> str:
    # Register
    r = client.post("/register", json={"username": username, "email": email, "password": password})
    assert r.status_code in (200, 400)
    # Login
    r = client.post("/login", json={"username": username, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return token


class TestSecurity:
    def test_input_validation_authenticated(self):
        token = _register_and_login()
        headers = {"Authorization": f"Bearer {token}"}

        test_cases = [
            {"input": "What is artificial intelligence?", "expected": 200},
            {"input": "<script>alert('xss')</script>", "expected": 400},
            {"input": "", "expected": 400},
            {"input": "a" * 2001, "expected": 400},
        ]

        for case in test_cases:
            resp = client.post("/query", json={"question": case["input"]}, headers=headers)
            assert resp.status_code == case["expected"]

    def test_security_headers_on_index(self):
        resp = client.get("/")
        headers = resp.headers
        required = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy",
        ]
        for h in required:
            assert h in headers

    def test_session_cookie_set_on_query(self):
        token = _register_and_login("secuser2", "sec2@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post("/query", json={"question": "hello"}, headers=headers)
        # May be 200 or 500 depending on LLM availability; cookie still should be set
        assert "session_id" in resp.cookies