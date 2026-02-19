"""
FocusGuard - Main Client Application
System tray application with real-time proctoring
"""

import sys
import os
import cv2
import numpy as np
from datetime import datetime
import threading
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, 
    QWidget, QVBoxLayout, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QPixmap, QAction, QColor, QPainter

from client.ai_engine import FaceDetector, GeometryCalculator, BehaviorClassifier, ViolationDetector
from client.network import SyncWebSocketClient
from client.anti_cheat import get_anti_cheat_monitor, CheatViolation, CheatEvent
from shared.constants import Config, BehaviorLabel, VIOLATION_MESSAGES, StatusColor


class StatusSignals(QObject):
    """Signals for thread-safe UI updates"""
    status_changed = pyqtSignal(str, str)  # status_text, color
    violation_detected = pyqtSignal(int, float)  # label, confidence


class ProctorEngine(threading.Thread):
    """
    Background thread running the AI proctoring engine
    Captures webcam → Detects face → Classifies behavior → Reports violations
    """
    
    def __init__(
        self, 
        signals: StatusSignals,
        ws_client: SyncWebSocketClient,
        camera_index: int = 0,
        exam_code: str = None,
        token: str = None,
        student_id: str = None
    ):
        super().__init__(daemon=True)
        self.signals = signals
        self.ws_client = ws_client
        self.camera_index = camera_index
        self.exam_code = exam_code
        self.token = token
        self.student_id = student_id
        self.running = False
        
        # AI components (initialized in run)
        self.detector = None
        self.geometry = None
        self.classifier = None
        self.violation_detector = None
        self.screenshot_capture = None
        
        # Current frame for screenshot
        self.current_frame = None
    
    def run(self):
        """Main proctoring loop"""
        self.running = True
        
        # Initialize camera
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.signals.status_changed.emit("Camera Error", StatusColor.RED)
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.FRAME_HEIGHT)
        
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Initialize AI components
        try:
            self.detector = FaceDetector()
            self.geometry = GeometryCalculator(frame_width, frame_height)
            self.classifier = BehaviorClassifier()
            self.violation_detector = ViolationDetector(
                self.classifier, 
                violation_threshold=Config.VIOLATION_FRAME_COUNT
            )
            
            # Initialize screenshot capture
            from client.ai_engine.screenshot import ScreenshotCapture
            self.screenshot_capture = ScreenshotCapture()
            
            self.signals.status_changed.emit("Monitoring", StatusColor.GREEN)
        except Exception as e:
            self.signals.status_changed.emit(f"AI Error: {e}", StatusColor.RED)
            cap.release()
            return
        
        # Main loop
        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            # Store current frame for screenshot
            self.current_frame = frame.copy()
            
            # Detect face
            result = self.detector.detect_with_image_coords(frame)
            
            if result is None:
                self.signals.status_changed.emit("No Face", StatusColor.GRAY)
                time.sleep(0.033)  # ~30 FPS
                continue
            
            normalized_landmarks, _ = result
            
            # Extract features
            features, iris_gaze = self.geometry.extract_all_features(normalized_landmarks)
            
            # Detect violations
            is_violation, label, confidence = self.violation_detector.detect(features, iris_gaze)
            
            if is_violation:
                behavior = VIOLATION_MESSAGES.get(label, "Unknown")
                self.signals.status_changed.emit(f"VIOLATION: {behavior}", StatusColor.RED)
                self.signals.violation_detected.emit(label, confidence)
                
                # Capture screenshot
                screenshot_b64 = None
                if self.screenshot_capture and self.current_frame is not None:
                    try:
                        _, screenshot_b64, _ = self.screenshot_capture.capture_frame(
                            self.current_frame,
                            self.student_id or "unknown",
                            self.exam_code or "NO_EXAM",
                            behavior,
                            save_local=False
                        )
                    except Exception as e:
                        print(f"Screenshot error: {e}")
                
                # Send to server via API (with screenshot)
                self._send_violation_to_api(label, behavior, confidence, screenshot_b64)
                
                # Also send via WebSocket for real-time display
                if self.ws_client and self.ws_client.is_connected:
                    self.ws_client.send_violation(label, confidence)
            else:
                self.signals.status_changed.emit("Normal", StatusColor.GREEN)
            
            time.sleep(0.033)  # ~30 FPS
        
        # Cleanup
        cap.release()
        if self.detector:
            self.detector.release()
    
    def _send_violation_to_api(self, label: int, behavior: str, confidence: float, screenshot_b64: str = None):
        """Send violation with screenshot to server API"""
        if not self.exam_code or not self.token:
            return
        
        import requests
        try:
            response = requests.post(
                f"http://{Config.SERVER_HOST}:{Config.SERVER_PORT}/api/exams/{self.exam_code}/violation",
                params={
                    "behavior_type": label,
                    "behavior_name": behavior,
                    "confidence": confidence,
                    "screenshot": screenshot_b64
                },
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print(f"Violation recorded: {behavior} (count: {data.get('violation_count')})")
        except Exception as e:
            print(f"Failed to send violation: {e}")
    
    def stop(self):
        """Stop the proctoring engine"""
        self.running = False


class FocusGuardTray(QSystemTrayIcon):
    """
    System tray application for FocusGuard
    Shows status and violation count
    """
    
    def __init__(self, app: QApplication, student_id: str = "STUDENT_001", 
                 exam_code: str = None, token: str = None):
        super().__init__()
        
        self.app = app
        self.student_id = student_id
        self.exam_code = exam_code
        self.token = token
        self.violation_count = 0
        
        # Create signals
        self.signals = StatusSignals()
        self.signals.status_changed.connect(self.on_status_changed)
        self.signals.violation_detected.connect(self.on_violation_detected)
        
        # Initialize WebSocket client
        self.ws_client = SyncWebSocketClient(
            server_url=f"ws://{Config.SERVER_HOST}:{Config.SERVER_PORT}/ws",
            student_id=student_id
        )
        
        # Initialize proctoring engine with exam info
        self.engine = ProctorEngine(
            self.signals,
            self.ws_client,
            Config.CAMERA_INDEX,
            exam_code=exam_code,
            token=token,
            student_id=student_id
        )
        
        # Initialize anti-cheat monitor
        self.anti_cheat = get_anti_cheat_monitor(on_violation=self.on_anticheat_violation)
        self.anti_cheat.enable_focus_lock = True  # Restore focus when lost
        
        # Setup tray icon
        self.setup_tray()
        
        # Start services
        self.start()
    
    def setup_tray(self):
        """Setup system tray icon and menu"""
        # Create a simple colored icon
        self.set_icon_color(StatusColor.GRAY)
        
        # Create menu
        menu = QMenu()
        
        # Status item (non-clickable)
        self.status_action = QAction("Status: Starting...", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        
        # Violation count
        self.violation_action = QAction("Violations: 0", menu)
        self.violation_action.setEnabled(False)
        menu.addAction(self.violation_action)
        
        menu.addSeparator()
        
        # Connection status
        self.connection_action = QAction("Server: Connecting...", menu)
        self.connection_action.setEnabled(False)
        menu.addAction(self.connection_action)
        
        menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)
        self.setToolTip("FocusGuard - AI Proctoring")
        
        # Show tray icon
        self.show()
    
    def set_icon_color(self, color: str):
        """Create a simple colored icon"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Map color string to QColor
        if color == StatusColor.GREEN:
            qcolor = QColor(0, 200, 0)
        elif color == StatusColor.RED:
            qcolor = QColor(200, 0, 0)
        else:
            qcolor = QColor(128, 128, 128)
        
        painter.setBrush(qcolor)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()
        
        self.setIcon(QIcon(pixmap))
    
    def start(self):
        """Start proctoring and network services"""
        # Start WebSocket connection
        self.ws_client.start()
        
        # Update connection status periodically
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.update_connection_status)
        self.connection_timer.start(1000)
        
        # Start proctoring engine
        self.engine.start()
        
        # Start anti-cheat monitoring (no window target for tray app)
        self.anti_cheat.start_monitoring()
    
    def update_connection_status(self):
        """Update connection status in menu"""
        if self.ws_client.is_connected:
            self.connection_action.setText("Server: Connected")
        else:
            self.connection_action.setText("Server: Disconnected")
    
    def on_status_changed(self, status: str, color: str):
        """Handle status change from proctoring engine"""
        self.status_action.setText(f"Status: {status}")
        self.set_icon_color(color)
    
    def on_violation_detected(self, label: int, confidence: float):
        """Handle violation detection"""
        self.violation_count += 1
        self.violation_action.setText(f"Violations: {self.violation_count}")
        
        # Show notification
        behavior = VIOLATION_MESSAGES.get(label, "Unknown")
        self.showMessage(
            "FocusGuard Alert",
            f"Violation detected: {behavior}",
            QSystemTrayIcon.MessageIcon.Warning,
            3000
        )
    
    def on_anticheat_violation(self, violation: CheatViolation):
        """Handle anti-cheat violation detection"""
        self.violation_count += 1
        self.violation_action.setText(f"Violations: {self.violation_count}")
        
        # Map cheat event to behavior label for reporting
        event_to_label = {
            CheatEvent.WINDOW_FOCUS_LOST: "Window Focus Lost",
            CheatEvent.ALT_TAB_DETECTED: "Alt+Tab Detected",
            CheatEvent.MINIMIZE_DETECTED: "Window Minimized",
            CheatEvent.MULTIPLE_MONITORS: "Multiple Monitors",
        }
        
        behavior_name = event_to_label.get(violation.event_type, violation.event_type.value)
        
        # Send to server
        if self.ws_client.is_connected:
            self.ws_client.send_violation(
                behavior=99,  # Special code for anti-cheat violations
                confidence=1.0,
                behavior_name=f"[AntiCheat] {behavior_name}"
            )
        
        # Show notification
        self.showMessage(
            "FocusGuard Security Alert",
            f"Anti-cheat: {behavior_name}",
            QSystemTrayIcon.MessageIcon.Critical,
            5000
        )
    
    def quit(self):
        """Clean shutdown"""
        self.anti_cheat.stop_monitoring()
        self.engine.stop()
        self.ws_client.stop()
        self.connection_timer.stop()
        self.app.quit()


def main():
    """Main entry point with login and exam join flow"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FocusGuard Client")
    parser.add_argument("--student-id", default=None, help="Student ID (overrides login)")
    parser.add_argument("--server", default=f"{Config.SERVER_HOST}:{Config.SERVER_PORT}", 
                        help="Server address (host:port)")
    parser.add_argument("--skip-login", action="store_true", help="Skip login (for testing)")
    args = parser.parse_args()
    
    # Parse server address
    if ":" in args.server:
        host, port = args.server.split(":")
        Config.SERVER_HOST = host
        Config.SERVER_PORT = int(port)
    
    print("=" * 60)
    print("FocusGuard - AI Proctoring Client")
    print("=" * 60)
    print(f"Server: {Config.SERVER_HOST}:{Config.SERVER_PORT}")
    print("=" * 60)
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Login flow
    token = None
    user = None
    exam_data = None
    student_id = args.student_id
    
    if not args.skip_login:
        try:
            from client.gui.login_dialog import LoginDialog
            from client.gui.exam_dialog import ExamJoinDialog
            
            # Show login dialog
            login_dialog = LoginDialog()
            if login_dialog.exec() != login_dialog.DialogCode.Accepted:
                print("Login cancelled")
                sys.exit(0)
            
            token = login_dialog.get_token()
            user = login_dialog.get_user()
            student_id = user.get("username") or user.get("student_id") or "STUDENT"
            
            print(f"Logged in as: {user.get('full_name')} ({user.get('role')})")
            
            # Show exam join dialog (only for students)
            if user.get("role") == "student":
                exam_dialog = ExamJoinDialog(token, user)
                if exam_dialog.exec() != exam_dialog.DialogCode.Accepted:
                    print("Exam join cancelled")
                    sys.exit(0)
                
                exam_data = exam_dialog.get_exam_data()
                print(f"Joined exam: {exam_data.get('exam_name')} ({exam_data.get('exam_code')})")
            else:
                print("Non-student role - skipping exam join")
                
        except ImportError as e:
            print(f"Login modules not available: {e}")
            print("Running in demo mode...")
    else:
        print("Skipping login (test mode)")
        student_id = student_id or "TEST_STUDENT"
    
    print(f"\nStudent ID: {student_id}")
    if exam_data:
        print(f"Exam: {exam_data.get('exam_name')} ({exam_data.get('exam_code')})")
    print("\nLook for the tray icon in your system tray!")
    print("Right-click on it to see status and quit.")
    print("=" * 60)
    
    # Create tray application with exam data
    exam_code = exam_data.get("exam_code") if exam_data else None
    tray = FocusGuardTray(app, student_id, exam_code=exam_code, token=token)
    
    # Run
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
