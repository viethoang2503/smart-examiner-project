"""
FocusGuard Database Models
SQLite database with SQLAlchemy ORM
"""

import os
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'focusguard.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==================== USER MODEL ====================

class User(Base):
    """User account model - created by school admin"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    
    # Role: 'admin', 'teacher', 'student'
    role = Column(String(20), default='student', nullable=False)
    
    # For students: class/grade info
    class_name = Column(String(50), nullable=True)
    student_id = Column(String(20), nullable=True)  # Mã số học sinh
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    violations = relationship("Violation", back_populates="user")
    exam_participations = relationship("ExamParticipant", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# ==================== EXAM SESSION MODEL ====================

class ExamSession(Base):
    """Exam session/room model"""
    __tablename__ = "exam_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_code = Column(String(10), unique=True, index=True, nullable=False)  # e.g., "ABC123"
    exam_name = Column(String(200), nullable=False)
    
    # Teacher who created the exam
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    teacher = relationship("User", foreign_keys=[teacher_id])
    
    # Timing
    exam_date = Column(DateTime, nullable=True)  # Scheduled exam date
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    
    # Status: 'pending', 'active', 'ended'
    status = Column(String(20), default='pending')
    
    # Settings
    duration_minutes = Column(Integer, default=60)
    max_violations = Column(Integer, default=5)  # Auto-flag if exceeded
    
    # Relationships
    participants = relationship("ExamParticipant", back_populates="exam")
    violations = relationship("Violation", back_populates="exam")
    
    def __repr__(self):
        return f"<ExamSession {self.exam_code}: {self.exam_name}>"


# ==================== EXAM PARTICIPANT ====================

class ExamParticipant(Base):
    """Student participation in an exam"""
    __tablename__ = "exam_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exam_sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Participation status
    joined_at = Column(DateTime, default=datetime.utcnow)
    left_at = Column(DateTime, nullable=True)
    is_online = Column(Boolean, default=False)
    
    # Violation count for this exam
    violation_count = Column(Integer, default=0)
    is_flagged = Column(Boolean, default=False)  # Flagged for too many violations
    
    # Relationships
    exam = relationship("ExamSession", back_populates="participants")
    user = relationship("User", back_populates="exam_participations")
    
    def __repr__(self):
        return f"<ExamParticipant user={self.user_id} exam={self.exam_id}>"


# ==================== VIOLATION MODEL ====================

class Violation(Base):
    """Violation record"""
    __tablename__ = "violations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("exam_sessions.id"), nullable=True)
    
    # Violation details
    behavior_type = Column(Integer, nullable=False)  # BehaviorLabel value
    behavior_name = Column(String(50), nullable=False)
    confidence = Column(String(10), nullable=False)  # Store as string for simplicity
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Optional screenshot path
    screenshot_path = Column(String(500), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="violations")
    exam = relationship("ExamSession", back_populates="violations")
    
    def __repr__(self):
        return f"<Violation {self.behavior_name} by user={self.user_id}>"


# ==================== DATABASE INITIALIZATION ====================

def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at: {DB_PATH}")


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_default_admin():
    """Create default admin account if not exists"""
    import bcrypt
    
    db = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            admin = User(
                username="admin",
                password_hash=password_hash,
                full_name="Administrator",
                role="admin",
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("Created default admin account: admin / admin123")
        return admin
    finally:
        db.close()



if __name__ == "__main__":
    print("Initializing FocusGuard Database...")
    init_db()
    create_default_admin()
    print("Done!")
