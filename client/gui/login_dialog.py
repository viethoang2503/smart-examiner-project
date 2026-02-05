"""
FocusGuard Login/Register Page for Client
PyQt6 login dialog with authentication
"""

import sys
import os
import requests
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# Add project path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.constants import Config


class LoginDialog(QDialog):
    """
    Login dialog for FocusGuard client
    Authenticates with server and returns JWT token
    """
    
    login_successful = pyqtSignal(dict)  # Emits user data on successful login
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.token = None
        self.user_data = None
        self.server_url = f"http://{Config.SERVER_HOST}:{Config.SERVER_PORT}"
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the login dialog UI"""
        self.setWindowTitle("FocusGuard - Đăng Nhập")
        self.setFixedSize(550, 520)
        
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
                font-size: 32px;
                font-weight: bold;
            }
            QLabel#subtitleLabel {
                color: #888888;
                font-size: 14px;
            }
            QLabel#fieldLabel {
                color: #ffcc00;
                font-size: 16px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #0f3460;
                color: #ffffff;
                border: 3px solid #00d4ff;
                border-radius: 12px;
                padding: 16px 20px;
                font-size: 20px;
            }
            QLineEdit:focus {
                border-color: #00ff88;
                background-color: #1a4a7a;
            }
            QLineEdit::placeholder {
                color: #666666;
            }
            QPushButton {
                background-color: #0f3460;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 18px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1a4a7a;
            }
            QPushButton#loginBtn {
                background-color: #00d4ff;
                color: #1a1a2e;
                font-size: 22px;
            }
            QPushButton#loginBtn:hover {
                background-color: #00ff88;
            }
            QPushButton#loginBtn:disabled {
                background-color: #555555;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(60, 45, 60, 45)
        
        # Logo/Title
        title = QLabel("FocusGuard")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("AI Proctoring System - Hệ thống giám sát thi cử")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(25)
        
        # Username field
        username_label = QLabel("Tên đăng nhập")
        username_label.setObjectName("fieldLabel")
        layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nhập tên đăng nhập...")
        self.username_input.setMinimumHeight(55)
        layout.addWidget(self.username_input)
        
        layout.addSpacing(8)
        
        # Password field
        password_label = QLabel("Mật khẩu")
        password_label.setObjectName("fieldLabel")
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Nhập mật khẩu...")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(55)
        layout.addWidget(self.password_input)
        
        layout.addSpacing(12)
        
        # Error message
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff4444; font-size: 14px; font-weight: bold;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_label)
        
        # Login button
        self.login_btn = QPushButton("ĐĂNG NHẬP")
        self.login_btn.setObjectName("loginBtn")
        self.login_btn.setMinimumHeight(60)
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)
        
        # Enter key triggers login
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
        
        # Server status
        self.status_label = QLabel(f"Server: {self.server_url}")
        self.status_label.setStyleSheet("color: #555555; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
    
    def handle_login(self):
        """Handle login button click"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            self.show_error("Please enter username and password")
            return
        
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Logging in...")
        self.error_label.setText("")
        
        try:
            # Call login API
            response = requests.post(
                f"{self.server_url}/api/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.user_data = data["user"]
                
                # Emit success signal
                self.login_successful.emit({
                    "token": self.token,
                    "user": self.user_data
                })
                
                self.accept()
            elif response.status_code == 401:
                self.show_error("Invalid username or password")
            else:
                self.show_error(f"Server error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.show_error("Cannot connect to server. Is it running?")
        except requests.exceptions.Timeout:
            self.show_error("Connection timeout")
        except Exception as e:
            self.show_error(f"Error: {str(e)}")
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Login")
    
    def show_error(self, message: str):
        """Display error message"""
        self.error_label.setText(message)
    
    def get_token(self) -> str:
        """Get the JWT token after successful login"""
        return self.token
    
    def get_user(self) -> dict:
        """Get user data after successful login"""
        return self.user_data


def show_login_dialog(server_url: str = None) -> dict:
    """
    Show login dialog and return user data if successful
    Returns None if login was cancelled
    """
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    dialog = LoginDialog()
    if server_url:
        dialog.server_url = server_url
        dialog.status_label.setText(f"Server: {server_url}")
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return {
            "token": dialog.get_token(),
            "user": dialog.get_user()
        }
    
    return None


if __name__ == "__main__":
    # Test the login dialog
    result = show_login_dialog()
    if result:
        print(f"Login successful!")
        print(f"User: {result['user']['full_name']} ({result['user']['role']})")
        print(f"Token: {result['token'][:50]}...")
    else:
        print("Login cancelled")
