"""
FocusGuard Authentication Module
JWT token-based authentication with password hashing
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.logging_config import get_auth_logger

auth_logger = get_auth_logger()

from .database import get_db, User, SessionLocal
from .config import settings

# ==================== CONFIG ====================

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_HOURS = settings.ACCESS_TOKEN_EXPIRE_HOURS

security = HTTPBearer()


# ==================== PYDANTIC MODELS ====================

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    username: str
    password: str
    full_name: str
    role: str = "student"
    class_name: Optional[str] = None
    student_id: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for login request"""
    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response (no password)"""
    id: int
    username: str
    full_name: str
    role: str
    class_name: Optional[str]
    student_id: Optional[str]
    is_active: bool
    must_change_password: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema for login response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    must_change_password: bool = False


class ChangePassword(BaseModel):
    """Schema for password change"""
    old_password: str
    new_password: str


# ==================== PASSWORD FUNCTIONS ====================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))



# ==================== JWT TOKEN FUNCTIONS ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# ==================== USER CRUD ====================

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    """Create a new user"""
    hashed_password = hash_password(user_data.password)
    
    user = User(
        username=user_data.username,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        class_name=user_data.class_name,
        student_id=user_data.student_id,
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password"""
    user = get_user_by_username(db, username)
    
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    return user


def change_user_password(db: Session, user: User, new_password: str) -> User:
    """Change user's password and clear must_change_password flag"""
    user.password_hash = hash_password(new_password)
    user.must_change_password = False  # Clear the forced change flag
    db.commit()
    db.refresh(user)
    return user


# ==================== DEPENDENCY - GET CURRENT USER ====================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    Use this in FastAPI endpoints: current_user: User = Depends(get_current_user)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    
    # Decode token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        auth_logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
    
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception
    
    # Get user from database
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        # Expunge user from session so it can be used after session closes
        db.expunge(user)
        return user
    finally:
        db.close()


def require_role(*roles: str):
    """
    Dependency factory for role-based access control
    Usage: Depends(require_role("admin", "teacher"))
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(roles)}"
            )
        return user
    return role_checker


# ==================== LOGIN FUNCTION ====================

def login_user(db: Session, username: str, password: str) -> Optional[TokenResponse]:
    """
    Authenticate user and return JWT token
    Returns None if authentication fails
    """
    user = authenticate_user(db, username, password)
    
    if not user:
        return None
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )
    
    # Check if user must change password (e.g., default admin)
    must_change = getattr(user, 'must_change_password', False) or False
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        must_change_password=must_change,
        user=UserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            class_name=user.class_name,
            student_id=user.student_id,
            is_active=user.is_active,
            must_change_password=must_change
        )
    )
