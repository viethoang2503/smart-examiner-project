"""
FocusGuard Authentication API Router
Login, register, and user management endpoints
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db, User, SessionLocal, init_db, create_default_admin
from .auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse, ChangePassword,
    get_current_user, require_role, login_user, create_user, get_user_by_username,
    verify_password, change_user_password, hash_password
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ==================== PUBLIC ENDPOINTS ====================

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """
    Login with username and password
    Returns JWT access token
    """
    db = SessionLocal()
    try:
        result = login_user(db, login_data.username, login_data.password)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        return result
    finally:
        db.close()


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        class_name=current_user.class_name,
        student_id=current_user.student_id,
        is_active=current_user.is_active
    )


@router.post("/change-password")
async def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user)
):
    """Change current user's password"""
    db = SessionLocal()
    try:
        # Verify old password
        user = db.query(User).filter(User.id == current_user.id).first()
        if not verify_password(data.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect old password"
            )
        
        # Change password
        change_user_password(db, user, data.new_password)
        
        return {"message": "Password changed successfully"}
    finally:
        db.close()


# ==================== ADMIN ENDPOINTS ====================

@router.post("/users", response_model=UserResponse)
async def create_new_user(
    user_data: UserCreate,
    current_user: User = Depends(require_role("admin"))
):
    """
    Create a new user account (Admin only)
    Used by school admin to create student/teacher accounts
    """
    db = SessionLocal()
    try:
        # Check if username exists
        existing = get_user_by_username(db, user_data.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Validate role
        if user_data.role not in ["admin", "teacher", "student"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be: admin, teacher, or student"
            )
        
        # Create user
        user = create_user(db, user_data)
        
        return UserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            class_name=user.class_name,
            student_id=user.student_id,
            is_active=user.is_active
        )
    finally:
        db.close()


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    role: Optional[str] = None,
    current_user: User = Depends(require_role("admin", "teacher"))
):
    """
    List all users (Admin/Teacher only)
    Teachers can only see students
    """
    db = SessionLocal()
    try:
        query = db.query(User)
        
        # Filter by role if specified
        if role:
            query = query.filter(User.role == role)
        
        # Teachers can only see students
        if current_user.role == "teacher":
            query = query.filter(User.role == "student")
        
        users = query.all()
        
        return [
            UserResponse(
                id=u.id,
                username=u.username,
                full_name=u.full_name,
                role=u.role,
                class_name=u.class_name,
                student_id=u.student_id,
                is_active=u.is_active
            )
            for u in users
        ]
    finally:
        db.close()


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_role("admin", "teacher"))
):
    """Get a specific user by ID"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            class_name=user.class_name,
            student_id=user.student_id,
            is_active=user.is_active
        )
    finally:
        db.close()


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    current_user: User = Depends(require_role("admin"))
):
    """Enable/disable a user account"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_active = not user.is_active
        db.commit()
        
        return {
            "message": f"User {'enabled' if user.is_active else 'disabled'}",
            "is_active": user.is_active
        }
    finally:
        db.close()


@router.put("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    new_password: str,
    current_user: User = Depends(require_role("admin"))
):
    """Reset a user's password (Admin only)"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.password_hash = hash_password(new_password)
        db.commit()
        
        return {"message": "Password reset successfully"}
    finally:
        db.close()


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_role("admin"))
):
    """Delete a user account (Admin only)"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Can't delete yourself
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        db.delete(user)
        db.commit()
        
        return {"message": "User deleted"}
    finally:
        db.close()


# ==================== BULK CREATE ====================

class BulkUserCreate(UserCreate):
    pass


@router.post("/users/bulk", response_model=List[UserResponse])
async def create_users_bulk(
    users: List[UserCreate],
    current_user: User = Depends(require_role("admin"))
):
    """
    Create multiple users at once (Admin only)
    Useful for importing class lists
    """
    db = SessionLocal()
    created = []
    
    try:
        for user_data in users:
            # Skip if username exists
            existing = get_user_by_username(db, user_data.username)
            if existing:
                continue
            
            user = create_user(db, user_data)
            created.append(UserResponse(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                role=user.role,
                class_name=user.class_name,
                student_id=user.student_id,
                is_active=user.is_active
            ))
        
        return created
    finally:
        db.close()


# ==================== INITIALIZATION ====================

def init_auth():
    """Initialize database and create default admin"""
    init_db()
    create_default_admin()
