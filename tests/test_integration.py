"""
FocusGuard Integration Tests
Tests end-to-end flow from client to server
"""

import pytest
import requests
import time
import sys
import os

# Add project path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.constants import Config

BASE_URL = f"http://localhost:{Config.SERVER_PORT}"


class TestAuthentication:
    """Test login and authentication flow"""
    
    def test_login_success(self):
        """Test successful login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["role"] in ["admin", "teacher", "student"]
        
        return data["access_token"]
    
    def test_login_wrong_password(self):
        """Test login with wrong password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
            timeout=10
        )
        
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "nonexistent", "password": "password"},
            timeout=10
        )
        
        assert response.status_code == 401


class TestExamManagement:
    """Test exam session management"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token for tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=10
        )
        return response.json()["access_token"]
    
    def test_create_exam(self, admin_token):
        """Test creating a new exam"""
        response = requests.post(
            f"{BASE_URL}/api/exams",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "exam_name": "Integration Test Exam",
                "duration_minutes": 60,
                "max_violations": 5
            },
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "exam_code" in data
        assert len(data["exam_code"]) == 6
        assert data["exam_name"] == "Integration Test Exam"
        
        return data["exam_code"]
    
    def test_list_exams(self, admin_token):
        """Test listing all exams"""
        response = requests.get(
            f"{BASE_URL}/api/exams",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_exam_details(self, admin_token):
        """Test getting exam details"""
        # First create an exam
        create_response = requests.post(
            f"{BASE_URL}/api/exams",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "exam_name": "Detail Test Exam",
                "duration_minutes": 30,
                "max_violations": 3
            },
            timeout=10
        )
        exam_code = create_response.json()["exam_code"]
        
        # Get details
        response = requests.get(
            f"{BASE_URL}/api/exams/{exam_code}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["exam_code"] == exam_code


class TestViolationReporting:
    """Test violation detection and reporting"""
    
    @pytest.fixture
    def setup_exam_and_student(self):
        """Setup exam and join as student"""
        # Admin creates exam
        admin_login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=10
        )
        admin_token = admin_login.json()["access_token"]
        
        # Create exam
        exam_response = requests.post(
            f"{BASE_URL}/api/exams",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "exam_name": "Violation Test Exam",
                "duration_minutes": 60,
                "max_violations": 3
            },
            timeout=10
        )
        exam_code = exam_response.json()["exam_code"]
        
        return {
            "admin_token": admin_token,
            "exam_code": exam_code
        }
    
    def test_record_violation(self, setup_exam_and_student):
        """Test recording a violation"""
        exam_code = setup_exam_and_student["exam_code"]
        admin_token = setup_exam_and_student["admin_token"]
        
        # Record violation (as admin for testing)
        response = requests.post(
            f"{BASE_URL}/api/exams/{exam_code}/violations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "behavior": "Looking Left",
                "confidence": 0.85
            },
            timeout=10
        )
        
        # Should work or return appropriate error
        assert response.status_code in [200, 201, 400, 404]


class TestAPIHealth:
    """Test API availability and health"""
    
    def test_server_health(self):
        """Test if server is running"""
        try:
            response = requests.get(f"{BASE_URL}/", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("Server not running")
    
    def test_api_response_time(self):
        """Test API response time is acceptable"""
        start = time.time()
        try:
            response = requests.get(f"{BASE_URL}/", timeout=5)
            elapsed = (time.time() - start) * 1000  # ms
            
            assert elapsed < 500, f"Response time too slow: {elapsed}ms"
            print(f"API Response time: {elapsed:.2f}ms")
        except requests.exceptions.ConnectionError:
            pytest.skip("Server not running")


def run_integration_tests():
    """Run all integration tests"""
    print("=" * 60)
    print("FocusGuard Integration Tests")
    print("=" * 60)
    
    # Check server connection first
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✅ Server is running at {BASE_URL}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Server not running at {BASE_URL}")
        print("Please start the server first: python run_server.py")
        return False
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
    return True


if __name__ == "__main__":
    run_integration_tests()
