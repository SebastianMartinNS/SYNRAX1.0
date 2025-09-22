import sys
from pathlib import Path
import asyncio
import logging
import datetime
import time
from logging.handlers import RotatingFileHandler
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Response, Depends, status, UploadFile, File
import aiofiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
from pythonjsonlogger import jsonlogger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from contextlib import asynccontextmanager

# Add parent directory to Python path for local imports
sys.path.append(str(Path(__file__).parent))

from src.cache import CacheManager, get_report_cache_key
from src.models import User as DBUser, Conversation, Message, get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.config import Config
from src.agent_new2 import AIAgent
from src.security import SessionManager, InputValidator, SecurityMiddleware

# Authentication models
class UserSchema(BaseModel):
    id: Optional[int] = None
    username: str
    email: str
    created_at: Optional[datetime] = None
    disabled: bool = False

class UserInDB(UserSchema):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# In-memory user database (for demo; use real DB in production)
# REMOVED: fake_users_db replaced with database models

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db: Session, username: str):
    return db.query(DBUser).filter(DBUser.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

class Bearer401(HTTPBearer):
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        try:
            return await super().__call__(request)
        except HTTPException as e:
            if e.status_code == status.HTTP_403_FORBIDDEN:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
            raise

auth_scheme = Bearer401()

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(auth_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    # Convert DB model to Pydantic schema including fields used by routes
    return UserSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
        disabled=not user.is_active
    )

async def get_current_active_user(current_user: UserSchema = Depends(get_current_user)):
    if hasattr(current_user, 'disabled') and current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    # Se è un modello DB, controlla is_active
    if hasattr(current_user, 'is_active') and not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Configure logging
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        # Use the directly imported datetime/timezone to avoid name shadowing
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['message'] = record.getMessage()

log_formatter = CustomJsonFormatter()

# Ensure logs directory exists
logs_dir = (Path('.') / 'logs').resolve()
logs_dir.mkdir(parents=True, exist_ok=True)

# App log handler (10MB, 5 backup)
app_handler = RotatingFileHandler(
    str(logs_dir / 'app.log'),
    maxBytes=10*1024*1024,
    backupCount=5
)
app_handler.setFormatter(log_formatter)

# Security log handler
security_handler = RotatingFileHandler(
    str(logs_dir / 'security.log'),
    maxBytes=5*1024*1024,
    backupCount=10
)
security_handler.setFormatter(log_formatter)

# Console handler with human-readable format for development
console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(console_formatter)

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[app_handler, stream_handler]
)

# Get logger instances
logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')
uvicorn_logger = logging.getLogger('uvicorn')

# Set log levels
logger.setLevel(logging.DEBUG)
security_logger.addHandler(security_handler)
security_logger.setLevel(logging.INFO)
uvicorn_logger.setLevel(logging.DEBUG)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    try:
        if config.admin_username and config.admin_password and config.admin_email:
            # Create admin user if not exists
            from sqlalchemy.orm import Session as _Session
            for db in get_db():
                assert isinstance(db, _Session)
                existing = db.query(DBUser).filter(DBUser.username == config.admin_username).first()
                if not existing:
                    admin_user = DBUser(
                        username=config.admin_username,
                        email=config.admin_email,
                        hashed_password=get_password_hash(config.admin_password),
                        is_active=True
                    )
                    db.add(admin_user)
                    db.commit()
                    logger.info(f"Provisioned admin user: {config.admin_username}")
                break
    except Exception as e:
        logger.error(f"Admin provisioning failed: {e}")
    yield
    # Shutdown code (if needed)

# Initialize FastAPI app
app = FastAPI(
    title="Synrax AI Agent",
    description="A secure AI assistant with RAG capabilities",
    version="1.0.0",
    debug=True,
    docs_url="/docs" if logging.root.level == logging.DEBUG else None,
    lifespan=lifespan
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

start_time = time.time()

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
else:
    logger.warning(f"Static directory not found: {static_dir}")

# Initialize configuration and components
try:
    config = Config()
    SECRET_KEY = config.secret_key
    agent = AIAgent(config=config)
    session_manager = SessionManager(config.secret_key, config.session_lifetime)
    input_validator = InputValidator()
    cache_manager = CacheManager(config)
    logger.info("Application components initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize application components: {str(e)}", exc_info=True)
    raise

# Add security middleware
app.add_middleware(SecurityMiddleware, config=config, debug=app.debug)

# Initialize CORS
allow_all = config.cors_origins == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=False if allow_all else True,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["*"]
)

# Optional: auto-provision single admin user if configured (moved to lifespan handler)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Number of active connections')
QUERY_COUNT = Counter('ai_queries_total', 'Total AI queries processed')
ERROR_COUNT = Counter('errors_total', 'Total errors', ['type'])
AUTH_ATTEMPTS = Counter('auth_attempts_total', 'Total authentication attempts', ['result'])
UPLOAD_COUNT = Counter('file_uploads_total', 'Total file uploads')
USER_REGISTRATIONS = Counter('user_registrations_total', 'Total user registrations')
CONVERSATION_COUNT = Counter('conversations_total', 'Total conversations created')
MESSAGE_COUNT = Counter('messages_total', 'Total messages sent')

# Cache for security report
report_cache = None
report_lock = asyncio.Lock()
REPORT_SCHEMA_VERSION = 2

# Route handlers
@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the main application page"""
    logger.info("Chiamata alla route / (index)")
    with open(Path(__file__).parent / 'templates' / 'index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.post("/query")
@limiter.limit("10/minute")
async def query(request: Request, current_user: UserSchema = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Handle chat queries"""
    start_time = time.time()
    try:
        # Get client ID for session management
        client_id = request.client.host if request.client else "unknown"

        # Validate session if exists
        session_id = request.cookies.get("session_id")
        logger.info(f"Request from {client_id}, session_id: {session_id}")

        if session_id and not session_manager.validate_session(session_id):
            logger.warning(f"Invalid session {session_id} from {client_id}")
            REQUEST_COUNT.labels(method='POST', endpoint='/query', status='401').inc()
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        # Parse and validate input
        data = await request.json()
        question = data.get("question", "")
        conversation_id = data.get("conversation_id")

        # Input validation
        if not input_validator.validate_query(question):
            REQUEST_COUNT.labels(method='POST', endpoint='/query', status='400').inc()
            logger.warning(f"Invalid query attempt from {client_id}: {question[:100]}")
            raise HTTPException(status_code=400, detail="Invalid query")

        # Get or create conversation
        if conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation
            conversation = Conversation(
                user_id=current_user.id,
                title=question[:50] + "..." if len(question) > 50 else question
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            CONVERSATION_COUNT.inc()

        # Process query
        sanitized_question = input_validator.sanitize_text(question)
        
        # Audit log the query
        security_logger.info(f"User {current_user.username} queried: {sanitized_question[:100]}{'...' if len(sanitized_question) > 100 else ''}")
        
        response = agent.query(sanitized_question)

        # Save messages to database
        user_message = Message(
            conversation_id=conversation.id,
            role="human",
            content=sanitized_question
        )
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=response["answer"]
        )

        db.add(user_message)
        db.add(assistant_message)
        db.commit()
        MESSAGE_COUNT.inc(2)  # Increment for both user and assistant messages

        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Increment query counter
        QUERY_COUNT.inc()

        # Process sources
        sources = []
        for doc in response.get("source_documents", []):
            if hasattr(doc, 'page_content'):
                source_text = doc.page_content[:60] + ("..." if len(doc.page_content) > 60 else "")
                sources.append(input_validator.sanitize_text(source_text))

        # Create or update session
        if not session_id:
            session_id = session_manager.create_session(client_id)

        # Prepare response
        json_response = JSONResponse({
            "answer": input_validator.sanitize_text(response["answer"]),
            "sources": sources,
            "conversation_id": conversation.id
        })

        # Set session cookie
        json_response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=config.session_lifetime
        )

        REQUEST_COUNT.labels(method='POST', endpoint='/query', status='200').inc()
        REQUEST_LATENCY.labels(method='POST', endpoint='/query').observe(time.time() - start_time)

        return json_response

    except HTTPException:
        raise
    except Exception as e:
        ERROR_COUNT.labels(type='query_error').inc()
        REQUEST_COUNT.labels(method='POST', endpoint='/query', status='500').inc()
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/report")
async def report(request: Request, current_user: UserSchema = Depends(get_current_active_user)):
    """Generate and return a security report"""
    try:
        # Check Redis cache first
        cache_key = get_report_cache_key()
        cached_report = cache_manager.get(cache_key)
        if cached_report:
            return JSONResponse({"status": "ready", "report": cached_report})

        # If not in cache, generate in background
        if report_lock.locked():
            return JSONResponse(status_code=202, content={"status": "generating"})

        asyncio.create_task(generate_report_background())
        return JSONResponse(status_code=202, content={"status": "started"})
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

async def generate_report_background():
    """Generate security report in background"""
    async with report_lock:
        try:
            logger.info("Starting background report generation...")
            loop = asyncio.get_running_loop()
            report = await loop.run_in_executor(None, agent.generate_security_report)

            # Cache in Redis
            cache_key = get_report_cache_key()
            cache_data = {"status": "success", "version": REPORT_SCHEMA_VERSION, "data": report}
            cache_manager.set(cache_key, cache_data, ttl=config.cache_ttl)

            logger.info("Background report generation completed successfully")
        except Exception as e:
            logger.error(f"Background report generation failed: {str(e)}", exc_info=True)
            # Cache error state
            cache_key = get_report_cache_key()
            error_data = {"status": "error", "message": str(e)}
            cache_manager.set(cache_key, error_data, ttl=300)  # Cache errors for 5 minutes

@app.get("/conversations")
async def list_conversations(current_user: UserSchema = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """List conversations for the current user"""
    convs = db.query(Conversation).filter(Conversation.user_id == current_user.id).order_by(Conversation.updated_at.desc()).all()
    return {"conversations": [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None
        } for c in convs
    ]}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if components are initialized
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                "config": "ok",
                "agent": "ok" if agent else "error",
                "llm": "ok" if agent and agent.llm else "warning",
                "rag": "ok",
                "memory": "ok"
            }
        }
        
        # Avoid slow external checks here; provide a cheap readiness signal only
        
        return JSONResponse(health_status)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            {"status": "unhealthy", "error": str(e)}, 
            status_code=500
        )

@app.get("/metrics")
async def metrics(current_user: UserSchema = Depends(get_current_active_user)):
    """Prometheus metrics endpoint"""
    try:
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate metrics")

@app.post("/register", response_model=UserSchema)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Optionally disable public registration for single-user mode
    if not getattr(config, 'allow_user_registration', True):
        raise HTTPException(status_code=403, detail="User registration is disabled")
    # Check if user already exists
    db_user = get_user(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Check if email already exists
    email_exists = db.query(DBUser).filter(DBUser.email == user.email).first()
    if email_exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = DBUser(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        is_active=True
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        USER_REGISTRATIONS.inc()
        security_logger.info(f"User registration successful: {user.username}")
        return UserSchema(username=db_user.username, email=db_user.email, disabled=not db_user.is_active)
    except IntegrityError:
        db.rollback()
        security_logger.warning(f"User registration failed - duplicate: {user.username}")
        raise HTTPException(status_code=400, detail="Registration failed")

@app.post("/login", response_model=Token)
async def login_for_access_token(form_data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        security_logger.warning(f"Failed login attempt for user: {form_data.username}")
        AUTH_ATTEMPTS.labels(result='failed').inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    security_logger.info(f"User {user.username} logged in successfully")
    AUTH_ATTEMPTS.labels(result='success').inc()
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserSchema)
async def read_users_me(current_user: UserSchema = Depends(get_current_active_user)):
    return current_user

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: UserSchema = Depends(get_current_active_user)):
    """Upload and ingest a document into RAG system"""
    try:
        # Validate file type (restrict to safe text formats by default)
        allowed_types = ['text/plain', 'text/markdown']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        # Enforce size limit (~1MB) to protect memory
        content = await file.read()
        max_size = 1 * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(status_code=413, detail="File too large")

        # Decode content safely
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Invalid text encoding; use UTF-8")
        
        # Ingest into RAG
        agent.ingest_documents([text_content])
        
        # Audit log the upload
        security_logger.info(f"User {current_user.username} uploaded file: {file.filename} ({len(content)} bytes)")
        
        UPLOAD_COUNT.inc()
        return {"message": f"File {file.filename} ingested successfully"}
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file")

@app.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int, current_user: UserSchema = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get messages for a specific conversation"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at).all()

    return {"messages": [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        } for msg in messages
    ]}

@app.get("/stats")
async def get_stats(current_user: UserSchema = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get system statistics"""
    try:
        # User-specific stats
        user_conversations = db.query(Conversation).filter(Conversation.user_id == current_user.id).count()
        user_messages = db.query(Message).join(Conversation).filter(Conversation.user_id == current_user.id).count()

        # System-wide stats (admin only)
        configured_admin = getattr(config, 'admin_username', None) or "admin"
        is_admin = current_user.username == configured_admin
        system_stats = {}
        if is_admin:
            total_users = db.query(DBUser).count()
            total_conversations = db.query(Conversation).count()
            total_messages = db.query(Message).count()

            system_stats = {
                "total_users": total_users,
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "avg_conversations_per_user": total_conversations / total_users if total_users > 0 else 0,
                "avg_messages_per_conversation": total_messages / total_conversations if total_conversations > 0 else 0
            }

        return {
            "uptime": time.time() - start_time,
            "user_stats": {
                "conversations_count": user_conversations,
                "messages_count": user_messages,
                "account_created": current_user.created_at.isoformat() if getattr(current_user, 'created_at', None) else None
            },
            "system_stats": system_stats if is_admin else None
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return {
            "uptime": time.time() - start_time,
            "error": "Failed to retrieve detailed statistics"
        }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="debug")