import re
import time
import logging
import functools
import secrets
from typing import Optional, Dict, Any, Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
from html import escape

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('security.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""
    def __init__(self, app, config, debug: bool = False):
        super().__init__(app)
        self.config = config
        self.debug = debug
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            # Host validation
            host = request.headers.get("host", "").split(":")[0]
            if not self.config.is_allowed_host(host):
                logger.warning(f"Invalid host header: {host}")
                raise HTTPException(status_code=400, detail="Invalid host header")

            # Request size validation
            content_length = request.headers.get("content-length", 0)
            if int(content_length) > self.config.max_request_size:
                logger.warning(f"Request too large: {content_length} bytes")
                raise HTTPException(status_code=413, detail="Request too large")

            # Process request
            response = await call_next(request)

            # Add security headers
            response.headers.update(self.config.get_security_headers(self.debug))
            
            return response

        except HTTPException as e:
            logger.error(f"Security violation: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # Rate limiting is handled by slowapi in the app; no client-id helper needed here.

class InputValidator:
    """Input validation and sanitization"""
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Minimal sanitization; apply escaping only when rendering in HTML UI, not for JSON."""
        return text.strip()
    
    @staticmethod
    def validate_query(query: str) -> bool:
        """Validate query input: non-empty and within length; basic tag check."""
        if not query or len(query.strip()) == 0:
            return False
        if len(query) > 2000:
            return False
        # Very basic HTML tag injection avoidance; enforce escaping at render.
        if re.search(r"<\s*script", query, re.IGNORECASE):
            return False
        return True

class SessionManager:
    """Secure session management"""
    def __init__(self, secret_key: str, lifetime: int):
        self.secret_key = secret_key
        self.lifetime = lifetime
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, client_id: str) -> str:
        """Create a new session"""
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            'client_id': client_id,
            'created_at': time.time(),
            'last_accessed': time.time()
        }
        return session_id
    
    def validate_session(self, session_id: str) -> bool:
        """Validate session and check expiration"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        current_time = time.time()
        
        # Check session expiration
        if current_time - session['created_at'] > self.lifetime:
            del self.sessions[session_id]
            return False
        
        # Update last accessed time
        session['last_accessed'] = current_time
        return True
    
    def end_session(self, session_id: str) -> None:
        """End a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]