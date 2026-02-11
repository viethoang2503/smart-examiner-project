"""
FocusGuard - Database Tests
Tests for database models and operations
"""

import pytest
import os
import sys
import tempfile
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabaseModels:
    """Test database models"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        # Create temp file
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Import and configure database
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from server.database import Base, User, ExamSession, Violation, ExamParticipant
        
        engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        yield {
            'session': session,
            'User': User,
            'Exam': ExamSession,
            'Violation': Violation,
            'ExamParticipant': ExamParticipant,
            'db_path': db_path
        }
        
        # Cleanup
        session.close()
        os.remove(db_path)
    
    def test_create_user(self, temp_db):
        """Test creating a user"""
        session = temp_db['session']
        User = temp_db['User']
        
        user = User(
            username="testuser",
            password_hash="hashed_password",
            full_name="Test User",
            role="student"
        )
        
        session.add(user)
        session.commit()
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.is_active == True
        print(f"✅ Created user with ID: {user.id}")
    
    def test_user_roles(self, temp_db):
        """Test different user roles"""
        session = temp_db['session']
        User = temp_db['User']
        
        roles = ['admin', 'teacher', 'student']
        
        for role in roles:
            user = User(
                username=f"user_{role}",
                password_hash="hash",
                full_name=f"{role.title()} User",
                role=role
            )
            session.add(user)
        
        session.commit()
        
        users = session.query(User).all()
        assert len(users) == 3
        print(f"✅ Created users with roles: {roles}")
    
    def test_create_exam(self, temp_db):
        """Test creating an exam"""
        session = temp_db['session']
        User = temp_db['User']
        Exam = temp_db['Exam']
        
        # Create teacher first
        teacher = User(
            username="teacher1",
            password_hash="hash",
            full_name="Teacher One",
            role="teacher"
        )
        session.add(teacher)
        session.commit()
        
        # Create exam
        exam = Exam(
            exam_code="ABC123",
            exam_name="Test Exam",
            teacher_id=teacher.id,
            duration_minutes=60,
            status="pending"
        )
        session.add(exam)
        session.commit()
        
        assert exam.id is not None
        assert exam.exam_code == "ABC123"
        assert exam.teacher_id == teacher.id
        print(f"✅ Created exam: {exam.exam_code}")
    
    def test_exam_participant(self, temp_db):
        """Test adding participant to exam"""
        session = temp_db['session']
        User = temp_db['User']
        Exam = temp_db['Exam']
        ExamParticipant = temp_db['ExamParticipant']
        
        # Create teacher and student
        teacher = User(username="t1", password_hash="h", full_name="Teacher", role="teacher")
        student = User(username="s1", password_hash="h", full_name="Student", role="student")
        session.add_all([teacher, student])
        session.commit()
        
        # Create exam
        exam = Exam(
            exam_code="EXM001",
            exam_name="Exam 1",
            teacher_id=teacher.id,
            duration_minutes=30
        )
        session.add(exam)
        session.commit()
        
        # Add participant
        participant = ExamParticipant(
            exam_id=exam.id,
            user_id=student.id
        )
        session.add(participant)
        session.commit()
        
        assert participant.id is not None
        assert participant.violation_count == 0
        assert participant.is_flagged == False
        print(f"✅ Added participant to exam")
    
    def test_record_violation(self, temp_db):
        """Test recording a violation"""
        session = temp_db['session']
        User = temp_db['User']
        Violation = temp_db['Violation']
        
        student = User(username="viol_student", password_hash="h", full_name="Student", role="student")
        session.add(student)
        session.commit()
        
        violation = Violation(
            user_id=student.id,
            exam_id=None,
            behavior_type=1,
            behavior_name="Looking Left",
            confidence="0.85",
            timestamp=datetime.now()
        )
        session.add(violation)
        session.commit()
        
        assert violation.id is not None
        assert violation.behavior_name == "Looking Left"
        assert violation.confidence == "0.85"
        print(f"✅ Recorded violation: {violation.behavior_name}")
    
    def test_multiple_violations(self, temp_db):
        """Test recording multiple violations"""
        session = temp_db['session']
        User = temp_db['User']
        Violation = temp_db['Violation']
        
        student = User(username="multi_viol", password_hash="h", full_name="Student", role="student")
        session.add(student)
        session.commit()
        
        violations_data = [
            ("Looking Left", 0.85),
            ("Head Down", 0.92),
            ("Talking", 0.78),
            ("Looking Right", 0.88)
        ]
        
        for i, (behavior, confidence) in enumerate(violations_data):
            violation = Violation(
                user_id=student.id,
                exam_id=None,
                behavior_type=i,
                behavior_name=behavior,
                confidence=str(confidence),
                timestamp=datetime.now()
            )
            session.add(violation)
        
        session.commit()
        
        all_violations = session.query(Violation).filter_by(user_id=student.id).all()
        assert len(all_violations) == 4
        print(f"✅ Recorded {len(all_violations)} violations")
    
    def test_flag_participant(self, temp_db):
        """Test flagging a participant"""
        session = temp_db['session']
        User = temp_db['User']
        Exam = temp_db['Exam']
        ExamParticipant = temp_db['ExamParticipant']
        
        teacher = User(username="t_flag", password_hash="h", full_name="Teacher", role="teacher")
        student = User(username="s_flag", password_hash="h", full_name="Student", role="student")
        session.add_all([teacher, student])
        session.commit()
        
        exam = Exam(exam_code="FLAG01", exam_name="Flag Test", teacher_id=teacher.id, duration_minutes=30)
        session.add(exam)
        session.commit()
        
        participant = ExamParticipant(exam_id=exam.id, user_id=student.id)
        session.add(participant)
        session.commit()
        
        # Flag the participant
        participant.is_flagged = True
        participant.violation_count = 5
        session.commit()
        
        # Verify
        p = session.query(ExamParticipant).get(participant.id)
        assert p.is_flagged == True
        assert p.violation_count == 5
        print(f"✅ Participant flagged with {p.violation_count} violations")


class TestDatabaseQueries:
    """Test database queries"""
    
    @pytest.fixture
    def populated_db(self):
        """Create database with test data"""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from server.database import Base, User, ExamSession, Violation, ExamParticipant
        
        engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Add test data
        teacher = User(username="teacher", password_hash="h", full_name="Teacher", role="teacher")
        students = [
            User(username=f"student{i}", password_hash="h", full_name=f"Student {i}", role="student")
            for i in range(5)
        ]
        session.add(teacher)
        session.add_all(students)
        session.commit()
        
        exam = ExamSession(exam_code="QUERY01", exam_name="Query Test", teacher_id=teacher.id, duration_minutes=60)
        session.add(exam)
        session.commit()
        
        # Add participants and violations
        for i, student in enumerate(students):
            participant = ExamParticipant(
                exam_id=exam.id, 
                user_id=student.id,
                violation_count=i,
                is_flagged=(i >= 3)
            )
            session.add(participant)
        
        session.commit()
        
        yield {
            'session': session,
            'User': User,
            'Exam': ExamSession,
            'Violation': Violation,
            'ExamParticipant': ExamParticipant,
            'exam': exam
        }
        
        session.close()
        os.remove(db_path)
    
    def test_query_users_by_role(self, populated_db):
        """Test querying users by role"""
        session = populated_db['session']
        User = populated_db['User']
        
        students = session.query(User).filter_by(role="student").all()
        teachers = session.query(User).filter_by(role="teacher").all()
        
        assert len(students) == 5
        assert len(teachers) == 1
        print(f"✅ Found {len(students)} students, {len(teachers)} teachers")
    
    def test_query_flagged_participants(self, populated_db):
        """Test querying flagged participants"""
        session = populated_db['session']
        ExamParticipant = populated_db['ExamParticipant']
        
        flagged = session.query(ExamParticipant).filter_by(is_flagged=True).all()
        
        assert len(flagged) == 2  # Students with index 3 and 4
        print(f"✅ Found {len(flagged)} flagged participants")
    
    def test_query_exam_by_code(self, populated_db):
        """Test querying exam by code"""
        session = populated_db['session']
        Exam = populated_db['Exam']
        
        exam = session.query(Exam).filter_by(exam_code="QUERY01").first()
        
        assert exam is not None
        assert exam.exam_name == "Query Test"
        print(f"✅ Found exam: {exam.exam_code}")
    
    def test_count_participants(self, populated_db):
        """Test counting participants in exam"""
        session = populated_db['session']
        ExamParticipant = populated_db['ExamParticipant']
        exam = populated_db['exam']
        
        count = session.query(ExamParticipant).filter_by(exam_id=exam.id).count()
        
        assert count == 5
        print(f"✅ Exam has {count} participants")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
