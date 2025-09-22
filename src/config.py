import os
import secrets
from typing import Optional
from urllib.parse import urlparse
from dotenv import load_dotenv
from pathlib import Path

class SecurityConfig:
    """Security-specific configuration settings"""
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
    MAX_REQUEST_SIZE = 1024 * 1024  # 1MB
    RATE_LIMIT = 60  # requests per minute
    SESSION_LIFETIME = 3600  # 1 hour
    CSP_POLICY = {
        'default-src': ["'self'"],
        # Remove unsafe-inline for production - only allow in debug mode
        'script-src': ["'self'"],
        'style-src': ["'self'"],
        'font-src': ["'self'"],
        'img-src': ["'self'", "data:", "blob:", "https://www.gstatic.com"],
        'connect-src': ["'self'", "ws:", "wss:", "http://localhost:11434"],
        'frame-src': ["'self'", "https://www.google.com", "https://translate.google.com"]
    }

class Config:
    """Main configuration class with security hardening"""
    def __init__(self):
        # Load environment variables from project .env regardless of CWD
        # Project layout: ai_agent/src/config.py -> .env is at ai_agent/.env
        env_path = (Path(__file__).resolve().parent.parent / '.env')
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
        else:
            # Fallback to default search path
            load_dotenv()

        # Generate secure session key if not exists
        self.secret_key_from_env = 'SECRET_KEY' in os.environ
        if not self.secret_key_from_env:
            raise ValueError("SECRET_KEY environment variable is required for production. Generate a secure key using: python -c 'import secrets; print(secrets.token_urlsafe(32))'")
        self.secret_key = os.getenv('SECRET_KEY')

        # Ollama configuration with validation
        self._validate_and_set_ollama_config()

        # Database configuration
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///./ai_agent.db')
        
        # Redis configuration
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.cache_enabled = self._parse_bool(os.getenv('CACHE_ENABLED', 'true'))
        self.cache_ttl = int(os.getenv('CACHE_TTL', '3600'))  # 1 hour default

        # Security settings
        self.security = SecurityConfig()

        # Rate limiting settings
        self.rate_limit_enabled = self._parse_bool(os.getenv('RATE_LIMIT_ENABLED', 'true'))
        self.rate_limit = int(os.getenv('RATE_LIMIT', str(SecurityConfig.RATE_LIMIT)))

        # Request size limits
        self.max_request_size = int(os.getenv('MAX_REQUEST_SIZE',
                                             str(SecurityConfig.MAX_REQUEST_SIZE)))

        # Logging configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'security.log')

        # Session configuration
        self.session_lifetime = int(os.getenv('SESSION_LIFETIME',
                                            str(SecurityConfig.SESSION_LIFETIME)))

        # CORS settings
        self.cors_origins = self._parse_cors_origins()

        # Admin / single-user settings (optional)
        self.admin_username = os.getenv('ADMIN_USERNAME') or None
        self.admin_email = os.getenv('ADMIN_EMAIL') or None
        self.admin_password = os.getenv('ADMIN_PASSWORD') or None
        # Allow disabling public registration to make the app single-user
        self.allow_user_registration = self._parse_bool(os.getenv('ALLOW_USER_REGISTRATION', 'true'))

    def _validate_and_set_ollama_config(self):
        """Validate and set Ollama configuration with security checks"""
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'mistral:7b-instruct')

        # Validate Ollama host URL
        try:
            parsed_url = urlparse(self.ollama_host)
            if parsed_url.scheme not in ['http', 'https']:
                raise ValueError('Invalid Ollama host URL scheme')
            if not parsed_url.netloc:
                raise ValueError('Invalid Ollama host URL')
        except Exception as e:
            raise ValueError(f'Invalid Ollama host URL: {str(e)}')

        # Validate model name
        if not isinstance(self.ollama_model, str) or not self.ollama_model.strip():
            raise ValueError('Invalid Ollama model name')

    def _parse_bool(self, value: str) -> bool:
        """Safely parse boolean values from environment variables"""
        return value.lower() in ('true', '1', 'yes', 'on')

    def _parse_cors_origins(self) -> list:
        """Parse and validate CORS origins"""
        origins = os.getenv('CORS_ORIGINS', '*')
        if origins == '*':
            return ['*']
        return [origin.strip() for origin in origins.split(',') if origin.strip()]

    def get_security_headers(self, debug: bool = False) -> dict:
        """Generate security headers for HTTP responses"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': self._build_csp_header(debug),
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }

    def _build_csp_header(self, debug: bool = False) -> str:
        """Build Content Security Policy header value"""
        policy = self.security.CSP_POLICY.copy()
        if debug:
            # Allow unsafe-inline only in debug mode
            policy['script-src'] = policy.get('script-src', []) + ["'unsafe-inline'"]
            policy['style-src'] = policy.get('style-src', []) + ["'unsafe-inline'"]

        return '; '.join(
            f"{key} {' '.join(values)}"
            for key, values in policy.items()
        )

    def is_allowed_host(self, host: str) -> bool:
        """Check if a host is allowed"""
        return host in self.security.ALLOWED_HOSTS
