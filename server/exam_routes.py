"""
FocusGuard Exam Session API Router
Create, manage, and monitor exam sessions
"""

import random
import string
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import SessionLocal, ExamSession, ExamParticipant, User, Violation
from .auth import get_current_user, require_role

router = APIRouter(prefix="/api/exams", tags=["Exams"])


# ==================== PYDANTIC MODELS ====================

class ExamCreate(BaseModel):
    """Create new exam session"""
    exam_name: str
    exam_date: Optional[str] = None  # Date in YYYY-MM-DD format
    duration_minutes: int = 60
    max_violations: int = 5


class ExamResponse(BaseModel):
    """Exam session response"""
    id: int
    exam_code: str
    exam_name: str
    teacher_id: int
    teacher_name: Optional[str] = None
    status: str
    exam_date: Optional[str] = None
    duration_minutes: int
    max_violations: int
    created_at: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    participant_count: int = 0
    online_count: int = 0


class ParticipantResponse(BaseModel):
    """Exam participant response"""
    id: int
    user_id: int
    username: str
    full_name: str
    class_name: Optional[str]
    is_online: bool
    violation_count: int
    is_flagged: bool
    joined_at: str


class JoinExamRequest(BaseModel):
    """Join exam request"""
    exam_code: str


# ==================== HELPER FUNCTIONS ====================

def generate_exam_code(length: int = 6) -> str:
    """Generate random exam code like ABC123"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== EXAM CRUD ====================

@router.post("", response_model=ExamResponse)
async def create_exam(
    exam_data: ExamCreate,
    current_user: User = Depends(require_role("admin", "teacher"))
):
    """Create a new exam session (Teacher/Admin only)"""
    db = SessionLocal()
    try:
        # Generate unique exam code
        while True:
            code = generate_exam_code()
            existing = db.query(ExamSession).filter(ExamSession.exam_code == code).first()
            if not existing:
                break
        
        # Parse exam date if provided
        exam_date = None
        if exam_data.exam_date:
            try:
                exam_date = datetime.strptime(exam_data.exam_date, "%Y-%m-%d")
            except ValueError:
                pass
        
        exam = ExamSession(
            exam_code=code,
            exam_name=exam_data.exam_name,
            teacher_id=current_user.id,
            exam_date=exam_date,
            duration_minutes=exam_data.duration_minutes,
            max_violations=exam_data.max_violations,
            status="pending"
        )
        
        db.add(exam)
        db.commit()
        db.refresh(exam)
        
        return ExamResponse(
            id=exam.id,
            exam_code=exam.exam_code,
            exam_name=exam.exam_name,
            teacher_id=exam.teacher_id,
            teacher_name=current_user.full_name,
            status=exam.status,
            exam_date=exam.exam_date.strftime("%Y-%m-%d") if exam.exam_date else None,
            duration_minutes=exam.duration_minutes,
            max_violations=exam.max_violations,
            created_at=exam.created_at.isoformat(),
            started_at=exam.started_at.isoformat() if exam.started_at else None,
            ended_at=exam.ended_at.isoformat() if exam.ended_at else None,
            participant_count=0,
            online_count=0
        )
    finally:
        db.close()


@router.get("", response_model=List[ExamResponse])
async def list_exams(
    status: Optional[str] = None,
    current_user: User = Depends(require_role("admin", "teacher"))
):
    """List all exam sessions"""
    db = SessionLocal()
    try:
        query = db.query(ExamSession)
        
        # Teachers see only their exams
        if current_user.role == "teacher":
            query = query.filter(ExamSession.teacher_id == current_user.id)
        
        if status:
            query = query.filter(ExamSession.status == status)
        
        exams = query.order_by(ExamSession.created_at.desc()).all()
        
        result = []
        for exam in exams:
            teacher = db.query(User).filter(User.id == exam.teacher_id).first()
            participants = db.query(ExamParticipant).filter(ExamParticipant.exam_id == exam.id).all()
            online = sum(1 for p in participants if p.is_online)
            
            result.append(ExamResponse(
                id=exam.id,
                exam_code=exam.exam_code,
                exam_name=exam.exam_name,
                teacher_id=exam.teacher_id,
                teacher_name=teacher.full_name if teacher else None,
                status=exam.status,
                exam_date=exam.exam_date.strftime("%Y-%m-%d") if exam.exam_date else None,
                duration_minutes=exam.duration_minutes,
                max_violations=exam.max_violations,
                created_at=exam.created_at.isoformat(),
                started_at=exam.started_at.isoformat() if exam.started_at else None,
                ended_at=exam.ended_at.isoformat() if exam.ended_at else None,
                participant_count=len(participants),
                online_count=online
            ))
        
        return result
    finally:
        db.close()


@router.get("/{exam_code}", response_model=ExamResponse)
async def get_exam(
    exam_code: str,
    current_user: User = Depends(get_current_user)
):
    """Get exam details by code"""
    db = SessionLocal()
    try:
        exam = db.query(ExamSession).filter(ExamSession.exam_code == exam_code.upper()).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        teacher = db.query(User).filter(User.id == exam.teacher_id).first()
        participants = db.query(ExamParticipant).filter(ExamParticipant.exam_id == exam.id).all()
        online = sum(1 for p in participants if p.is_online)
        
        return ExamResponse(
            id=exam.id,
            exam_code=exam.exam_code,
            exam_name=exam.exam_name,
            teacher_id=exam.teacher_id,
            teacher_name=teacher.full_name if teacher else None,
            status=exam.status,
            exam_date=exam.exam_date.strftime("%Y-%m-%d") if exam.exam_date else None,
            duration_minutes=exam.duration_minutes,
            max_violations=exam.max_violations,
            created_at=exam.created_at.isoformat(),
            started_at=exam.started_at.isoformat() if exam.started_at else None,
            ended_at=exam.ended_at.isoformat() if exam.ended_at else None,
            participant_count=len(participants),
            online_count=online
        )
    finally:
        db.close()


@router.post("/{exam_code}/join")
async def join_exam(
    exam_code: str,
    current_user: User = Depends(get_current_user)
):
    """Student joins an exam session"""
    if current_user.role not in ["student"]:
        raise HTTPException(status_code=403, detail="Only students can join exams")
    
    db = SessionLocal()
    try:
        exam = db.query(ExamSession).filter(ExamSession.exam_code == exam_code.upper()).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        if exam.status == "ended":
            raise HTTPException(status_code=400, detail="Exam has ended")
        
        # Check if already joined
        existing = db.query(ExamParticipant).filter(
            ExamParticipant.exam_id == exam.id,
            ExamParticipant.user_id == current_user.id
        ).first()
        
        if existing:
            existing.is_online = True
            db.commit()
            return {"message": "Rejoined exam", "exam_name": exam.exam_name}
        
        # Create new participant
        participant = ExamParticipant(
            exam_id=exam.id,
            user_id=current_user.id,
            is_online=True
        )
        db.add(participant)
        db.commit()
        
        return {
            "message": "Joined exam successfully",
            "exam_name": exam.exam_name,
            "exam_code": exam.exam_code,
            "status": exam.status,
            "duration_minutes": exam.duration_minutes
        }
    finally:
        db.close()


@router.post("/{exam_code}/start")
async def start_exam(
    exam_code: str,
    current_user: User = Depends(require_role("admin", "teacher"))
):
    """Start an exam session"""
    db = SessionLocal()
    try:
        exam = db.query(ExamSession).filter(ExamSession.exam_code == exam_code.upper()).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        if exam.status != "pending":
            raise HTTPException(status_code=400, detail=f"Exam is already {exam.status}")
        
        exam.status = "active"
        exam.started_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Exam started", "started_at": exam.started_at.isoformat()}
    finally:
        db.close()


@router.post("/{exam_code}/end")
async def end_exam(
    exam_code: str,
    current_user: User = Depends(require_role("admin", "teacher"))
):
    """End an exam session"""
    db = SessionLocal()
    try:
        exam = db.query(ExamSession).filter(ExamSession.exam_code == exam_code.upper()).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        exam.status = "ended"
        exam.ended_at = datetime.utcnow()
        
        # Mark all participants as offline
        participants = db.query(ExamParticipant).filter(ExamParticipant.exam_id == exam.id).all()
        for p in participants:
            p.is_online = False
        
        db.commit()
        
        return {"message": "Exam ended", "ended_at": exam.ended_at.isoformat()}
    finally:
        db.close()


@router.get("/{exam_code}/participants", response_model=List[ParticipantResponse])
async def get_participants(
    exam_code: str,
    current_user: User = Depends(require_role("admin", "teacher"))
):
    """Get all participants in an exam"""
    db = SessionLocal()
    try:
        exam = db.query(ExamSession).filter(ExamSession.exam_code == exam_code.upper()).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        participants = db.query(ExamParticipant).filter(ExamParticipant.exam_id == exam.id).all()
        
        result = []
        for p in participants:
            user = db.query(User).filter(User.id == p.user_id).first()
            if user:
                result.append(ParticipantResponse(
                    id=p.id,
                    user_id=p.user_id,
                    username=user.username,
                    full_name=user.full_name,
                    class_name=user.class_name,
                    is_online=p.is_online,
                    violation_count=p.violation_count,
                    is_flagged=p.is_flagged,
                    joined_at=p.joined_at.isoformat()
                ))
        
        return result
    finally:
        db.close()


@router.post("/{exam_code}/violation")
async def record_violation(
    exam_code: str,
    behavior_type: int,
    behavior_name: str,
    confidence: float,
    screenshot: Optional[str] = None,  # Base64 encoded image
    current_user: User = Depends(get_current_user)
):
    """Record a violation for a student in an exam with optional screenshot"""
    import base64
    import os
    
    db = SessionLocal()
    try:
        exam = db.query(ExamSession).filter(ExamSession.exam_code == exam_code.upper()).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        # Get participant
        participant = db.query(ExamParticipant).filter(
            ExamParticipant.exam_id == exam.id,
            ExamParticipant.user_id == current_user.id
        ).first()
        
        if not participant:
            raise HTTPException(status_code=400, detail="Not joined in this exam")
        
        # Save screenshot if provided
        screenshot_path = None
        if screenshot:
            try:
                # Create uploads directory
                uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'violations')
                os.makedirs(uploads_dir, exist_ok=True)
                
                # Generate filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{exam_code}_{current_user.username}_{timestamp}_{behavior_name}.jpg"
                filepath = os.path.join(uploads_dir, filename)
                
                # Decode and save
                img_data = base64.b64decode(screenshot)
                with open(filepath, 'wb') as f:
                    f.write(img_data)
                
                screenshot_path = f"/uploads/violations/{filename}"
            except Exception as e:
                print(f"Failed to save screenshot: {e}")
        
        # Record violation
        violation = Violation(
            user_id=current_user.id,
            exam_id=exam.id,
            behavior_type=behavior_type,
            behavior_name=behavior_name,
            confidence=str(confidence),
            screenshot_path=screenshot_path
        )
        db.add(violation)
        
        # Update participant violation count
        participant.violation_count += 1
        
        # Auto-flag if exceeded max violations
        if participant.violation_count >= exam.max_violations:
            participant.is_flagged = True
        
        db.commit()
        
        return {
            "message": "Violation recorded",
            "violation_count": participant.violation_count,
            "is_flagged": participant.is_flagged,
            "has_screenshot": screenshot_path is not None
        }
    finally:
        db.close()


class ViolationResponse(BaseModel):
    """Violation record response"""
    id: int
    user_id: int
    username: str
    full_name: str
    behavior_type: int
    behavior_name: str
    confidence: str
    timestamp: str
    screenshot_path: Optional[str] = None


@router.get("/{exam_code}/violations", response_model=List[ViolationResponse])
async def get_violations(
    exam_code: str,
    user_id: Optional[int] = None,
    current_user: User = Depends(require_role("admin", "teacher"))
):
    """Get all violations for an exam (with screenshots) for teacher reports"""
    db = SessionLocal()
    try:
        exam = db.query(ExamSession).filter(ExamSession.exam_code == exam_code.upper()).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        query = db.query(Violation).filter(Violation.exam_id == exam.id)
        
        if user_id:
            query = query.filter(Violation.user_id == user_id)
        
        violations = query.order_by(Violation.timestamp.desc()).all()
        
        result = []
        for v in violations:
            user = db.query(User).filter(User.id == v.user_id).first()
            if user:
                result.append(ViolationResponse(
                    id=v.id,
                    user_id=v.user_id,
                    username=user.username,
                    full_name=user.full_name,
                    behavior_type=v.behavior_type,
                    behavior_name=v.behavior_name,
                    confidence=v.confidence,
                    timestamp=v.timestamp.isoformat(),
                    screenshot_path=v.screenshot_path
                ))
        
        return result
    finally:
        db.close()


@router.delete("/{exam_code}")
async def delete_exam(
    exam_code: str,
    current_user: User = Depends(require_role("admin"))
):
    """Delete an exam (Admin only)"""
    db = SessionLocal()
    try:
        exam = db.query(ExamSession).filter(ExamSession.exam_code == exam_code.upper()).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        # Delete participants and violations
        db.query(ExamParticipant).filter(ExamParticipant.exam_id == exam.id).delete()
        db.query(Violation).filter(Violation.exam_id == exam.id).delete()
        db.delete(exam)
        db.commit()
        
        return {"message": "Exam deleted"}
    finally:
        db.close()
