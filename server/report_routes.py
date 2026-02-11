"""
FocusGuard Report API Routes
Endpoints for generating and downloading reports
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime

from .auth import get_current_user
from .database import get_db, ExamSession, Violation, ExamParticipant, User
from .reports import ReportGenerator

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{exam_code}/pdf")
async def download_pdf_report(
    exam_code: str,
    current_user: dict = Depends(get_current_user)
):
    """Download PDF report for an exam"""
    
    db = get_db()
    
    # Get exam
    exam = db.query(ExamSession).filter(ExamSession.exam_code == exam_code).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Check permission (admin/teacher only)
    if current_user.get('role') not in ['admin', 'teacher']:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get violations
    violations = db.query(Violation).filter(Violation.exam_code == exam_code).all()
    violation_list = []
    for v in violations:
        user = db.query(User).filter(User.id == v.user_id).first()
        violation_list.append({
            'timestamp': v.timestamp.isoformat() if v.timestamp else '',
            'student_name': user.full_name if user else 'Unknown',
            'behavior': v.behavior,
            'confidence': v.confidence
        })
    
    # Get participants
    participants = db.query(ExamParticipant).filter(
        ExamParticipant.exam_id == exam.id
    ).all()
    participant_list = []
    for p in participants:
        user = db.query(User).filter(User.id == p.user_id).first()
        participant_list.append({
            'full_name': user.full_name if user else 'Unknown',
            'violation_count': p.violation_count,
            'is_flagged': p.is_flagged
        })
    
    # Generate PDF
    generator = ReportGenerator()
    pdf_path = generator.generate_pdf_report(
        exam_name=exam.exam_name,
        exam_code=exam.exam_code,
        exam_date=exam.exam_date.strftime('%Y-%m-%d') if exam.exam_date else '',
        violations=violation_list,
        participants=participant_list
    )
    
    return FileResponse(
        path=pdf_path,
        filename=f"report_{exam_code}.pdf",
        media_type="application/pdf"
    )


@router.get("/{exam_code}/excel")
async def download_excel_report(
    exam_code: str,
    current_user: dict = Depends(get_current_user)
):
    """Download Excel report for an exam"""
    
    db = get_db()
    
    # Get exam
    exam = db.query(ExamSession).filter(ExamSession.exam_code == exam_code).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Check permission
    if current_user.get('role') not in ['admin', 'teacher']:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get violations
    violations = db.query(Violation).filter(Violation.exam_code == exam_code).all()
    violation_list = []
    for v in violations:
        user = db.query(User).filter(User.id == v.user_id).first()
        violation_list.append({
            'timestamp': v.timestamp.isoformat() if v.timestamp else '',
            'student_name': user.full_name if user else 'Unknown',
            'behavior': v.behavior,
            'confidence': v.confidence
        })
    
    # Get participants
    participants = db.query(ExamParticipant).filter(
        ExamParticipant.exam_id == exam.id
    ).all()
    participant_list = []
    for p in participants:
        user = db.query(User).filter(User.id == p.user_id).first()
        participant_list.append({
            'full_name': user.full_name if user else 'Unknown',
            'violation_count': p.violation_count,
            'is_flagged': p.is_flagged
        })
    
    # Generate Excel
    generator = ReportGenerator()
    excel_path = generator.generate_excel_report(
        exam_name=exam.exam_name,
        exam_code=exam.exam_code,
        exam_date=exam.exam_date.strftime('%Y-%m-%d') if exam.exam_date else '',
        violations=violation_list,
        participants=participant_list
    )
    
    return FileResponse(
        path=excel_path,
        filename=f"report_{exam_code}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.get("/{exam_code}/statistics")
async def get_exam_statistics(
    exam_code: str,
    current_user: dict = Depends(get_current_user)
):
    """Get statistics for an exam"""
    
    db = get_db()
    
    # Get exam
    exam = db.query(ExamSession).filter(ExamSession.exam_code == exam_code).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Get violations
    violations = db.query(Violation).filter(Violation.exam_code == exam_code).all()
    violation_list = [
        {
            'timestamp': v.timestamp.isoformat() if v.timestamp else '',
            'behavior': v.behavior,
            'confidence': v.confidence
        }
        for v in violations
    ]
    
    # Get participants
    participants = db.query(ExamParticipant).filter(
        ExamParticipant.exam_id == exam.id
    ).all()
    participant_list = [
        {
            'violation_count': p.violation_count,
            'is_flagged': p.is_flagged
        }
        for p in participants
    ]
    
    # Calculate statistics
    generator = ReportGenerator()
    stats = generator.get_statistics(violation_list, participant_list)
    
    return {
        "exam_code": exam_code,
        "exam_name": exam.exam_name,
        "statistics": stats
    }
