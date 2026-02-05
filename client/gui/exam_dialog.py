"""
FocusGuard Exam Join Dialog
Dialog for students to enter exam code after login
"""

import sys
import os
import requests
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from shared.constants import Config


class ExamJoinDialog(QDialog):
    """
    Dialog for students to enter exam code and join an exam session
    """
    
    exam_joined = pyqtSignal(dict)  # Emits exam data on successful join
    
    def __init__(self, token: str, user: dict, parent=None):
        super().__init__(parent)
        self.token = token
        self.user = user
        self.exam_data = None
        self.server_url = f"http://{Config.SERVER_HOST}:{Config.SERVER_PORT}"
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the exam join dialog UI"""
        self.setWindowTitle("FocusGuard - Join Exam")
        self.setFixedSize(520, 420)
        
        # Dark theme styling with high contrast
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                color: white;
            }
            QLabel {
                color: white;
            }
            QLabel#titleLabel {
                color: #00d4ff;
                font-size: 26px;
                font-weight: bold;
            }
            QLabel#welcomeLabel {
                color: #4caf50;
                font-size: 18px;
            }
            QLabel#instructionLabel {
                color: #aaaaaa;
                font-size: 16px;
            }
            QLabel#codeLabel {
                color: #ffcc00;
                font-size: 14px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #0f3460;
                color: #00ff88;
                border: 3px solid #00d4ff;
                border-radius: 12px;
                padding: 20px;
                font-size: 32px;
                font-weight: bold;
                letter-spacing: 12px;
                text-transform: uppercase;
            }
            QLineEdit:focus {
                border-color: #00ff88;
                background-color: #1a4a7a;
            }
            QLineEdit::placeholder {
                color: #666666;
                letter-spacing: 12px;
            }
            QPushButton {
                background-color: #0f3460;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 18px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1a4a7a;
            }
            QPushButton#joinBtn {
                background-color: #00d4ff;
                color: #1a1a2e;
                font-size: 20px;
            }
            QPushButton#joinBtn:hover {
                background-color: #00ff88;
            }
            QPushButton#joinBtn:disabled {
                background-color: #555555;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(50, 35, 50, 35)
        
        # Title
        title = QLabel("FocusGuard Exam")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Welcome message
        welcome = QLabel(f"Xin chào, {self.user.get('full_name', 'Sinh viên')}")
        welcome.setObjectName("welcomeLabel")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome)
        
        layout.addSpacing(15)
        
        # Instruction
        instruction = QLabel("Nhập mã bài thi để vào phòng thi")
        instruction.setObjectName("instructionLabel")
        instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instruction)
        
        # Code label
        code_label = QLabel("EXAM CODE")
        code_label.setObjectName("codeLabel")
        code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(code_label)
        
        # Exam code input
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("ABC123")
        self.code_input.setMaxLength(6)
        self.code_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_input.setMinimumHeight(70)
        layout.addWidget(self.code_input)
        
        # Error message
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff4444; font-size: 14px; font-weight: bold;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_label)
        
        layout.addSpacing(10)
        
        # Join button
        self.join_btn = QPushButton("VÀO PHÒNG THI")
        self.join_btn.setObjectName("joinBtn")
        self.join_btn.setMinimumHeight(60)
        self.join_btn.clicked.connect(self.handle_join)
        layout.addWidget(self.join_btn)
        
        # Enter key triggers join
        self.code_input.returnPressed.connect(self.handle_join)
        
        # Exam info (hidden initially)
        self.exam_info = QLabel("")
        self.exam_info.setStyleSheet("color: #4caf50; font-size: 14px; font-weight: bold;")
        self.exam_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.exam_info)
    
    def handle_join(self):
        """Handle join button click"""
        code = self.code_input.text().strip().upper()
        
        if len(code) != 6:
            self.show_error("Please enter a 6-character exam code")
            return
        
        self.join_btn.setEnabled(False)
        self.join_btn.setText("Joining...")
        self.error_label.setText("")
        
        try:
            # Call join API
            response = requests.post(
                f"{self.server_url}/api/exams/{code}/join",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.exam_data = {
                    "exam_code": code,
                    "exam_name": data.get("exam_name"),
                    "status": data.get("status"),
                    "duration_minutes": data.get("duration_minutes")
                }
                
                # Show success and close
                self.exam_info.setText(f"✓ Joined: {data.get('exam_name')}")
                self.exam_joined.emit(self.exam_data)
                self.accept()
                
            elif response.status_code == 404:
                self.show_error("Exam not found. Check the code.")
            elif response.status_code == 400:
                data = response.json()
                self.show_error(data.get("detail", "Cannot join exam"))
            elif response.status_code == 403:
                self.show_error("Only students can join exams")
            else:
                self.show_error(f"Error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.show_error("Cannot connect to server")
        except requests.exceptions.Timeout:
            self.show_error("Connection timeout")
        except Exception as e:
            self.show_error(f"Error: {str(e)}")
        finally:
            self.join_btn.setEnabled(True)
            self.join_btn.setText("Join Exam")
    
    def show_error(self, message: str):
        """Display error message"""
        self.error_label.setText(message)
    
    def get_exam_data(self) -> dict:
        """Get exam data after successful join"""
        return self.exam_data


def show_exam_join_dialog(token: str, user: dict) -> dict:
    """
    Show exam join dialog and return exam data if successful
    Returns None if cancelled
    """
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    dialog = ExamJoinDialog(token, user)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_exam_data()
    
    return None


if __name__ == "__main__":
    # Test the dialog
    result = show_exam_join_dialog("test_token", {"full_name": "Test Student"})
    if result:
        print(f"Joined exam: {result}")
    else:
        print("Cancelled")
