import pytest
import os
from unittest.mock import patch
from src.config import Config, SecurityConfig


class TestSecurityConfig:
    """Test SecurityConfig class"""

    def test_default_values(self):
        config = SecurityConfig()
        assert config.ALLOWED_HOSTS == ['localhost', '127.0.0.1', 'testserver']
        assert config.MAX_REQUEST_SIZE == 1024 * 1024
        assert config.RATE_LIMIT == 60
        assert config.SESSION_LIFETIME == 3600


class TestConfig:
    """Test Config class"""

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.config.load_dotenv')
    def test_missing_secret_key(self, mock_load_dotenv):
        """Test that missing SECRET_KEY raises error"""
        mock_load_dotenv.return_value = None  # Mock dotenv to not load anything
        with pytest.raises(ValueError, match="SECRET_KEY environment variable is required"):
            Config()

    @patch.dict(os.environ, {
        'OLLAMA_HOST': 'http://custom:8080',
        'OLLAMA_MODEL': 'llama2:7b',
        'RATE_LIMIT': '100'
    })
    def test_environment_variables(self):
        config = Config()
        assert config.ollama_host == 'http://custom:8080'
        assert config.ollama_model == 'llama2:7b'
        assert config.rate_limit == 100

    def test_invalid_ollama_host(self):
        with patch.dict(os.environ, {'OLLAMA_HOST': 'invalid-url'}):
            with pytest.raises(ValueError, match="Invalid Ollama host URL"):
                Config()

    def test_is_allowed_host(self):
        config = Config()
        assert config.is_allowed_host('localhost') is True
        assert config.is_allowed_host('127.0.0.1') is True
        assert config.is_allowed_host('testserver') is True
        assert config.is_allowed_host('evil.com') is False

    def test_get_security_headers(self):
        config = Config()
        headers = config.get_security_headers()
        required_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security',
            'Content-Security-Policy',
            'Referrer-Policy',
            'Permissions-Policy'
        ]
        for header in required_headers:
            assert header in headers

    def test_csp_debug_mode(self):
        """Test CSP allows unsafe-inline in debug mode"""
        config = Config()
        headers = config.get_security_headers(debug=True)
        csp = headers['Content-Security-Policy']
        assert "unsafe-inline" in csp

    def test_csp_production_mode(self):
        """Test CSP blocks unsafe-inline in production mode"""
        config = Config()
        headers = config.get_security_headers(debug=False)
        csp = headers['Content-Security-Policy']
        assert "unsafe-inline" not in csp