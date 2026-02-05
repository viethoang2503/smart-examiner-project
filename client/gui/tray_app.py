"""
FocusGuard - System Tray Application
PyQt6 tray icon for student proctoring client
"""

import sys
import os
import cv2
import threading
import time
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, 
    QWidget, QVBoxLayout, QLabel, QDialog, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QPixmap, QAction, QColor, QPainter, QFont

# Add parent/project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from client.ai_engine import FaceDetector, GeometryCalculator, BehaviorClassifier, ViolationDetector
from client.network import SyncWebSocketClient
from shared.constants import Config, BehaviorLabel, VIOLATION_MESSAGES, StatusColor


# ==================== SIGNALS ====================

class StatusSignals(QObject):
    """Signals for thread-safe UI updates"""
    status_changed = pyqtSignal(str, str)  # status_text, color
    violation_detected = pyqtSignal(int, float)  # label, confidence
    face_detected = pyqtSignal(bool)  # has_face


# ==================== PROCTOR ENGINE ====================

class ProctorEngine(threading.Thread):
    """
    Background thread running the AI proctoring engine
    Captures webcam → Detects face → Classifies behavior → Reports violations
    """
    
    def __init__(
        self, 
        signals: StatusSignals,
        ws_client: Optional[SyncWebSocketClient] = None,
        camera_index: int = 0
    ):
        super().__init__(daemon=True)
        self.signals = signals
        self.ws_client = ws_client
        self.camera_index = camera_index
        self.running = False
        
        # AI components
        self.detector = None
        self.geometry = None
        self.classifier = None
        self.violation_detector = None
        
        # Stats
        self.total_frames = 0
        self.faces_detected = 0
        self.violations_count = 0
    
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
            self.signals.status_changed.emit("Monitoring", StatusColor.GREEN)
        except Exception as e:
            self.signals.status_changed.emit(f"AI Error", StatusColor.RED)
            cap.release()
            return
        
        # Main loop
        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            self.total_frames += 1
            
            # Detect face
            result = self.detector.detect_with_image_coords(frame)
            
            if result is None:
                self.signals.face_detected.emit(False)
                self.signals.status_changed.emit("No Face", StatusColor.GRAY)
                time.sleep(0.033)
                continue
            
            self.faces_detected += 1
            self.signals.face_detected.emit(True)
            
            normalized_landmarks, _ = result
            
            # Extract features
            features = self.geometry.extract_all_features(normalized_landmarks)
            
            # Detect violations
            is_violation, label, confidence = self.violation_detector.detect(features)
            
            if is_violation:
                self.violations_count += 1
                behavior = VIOLATION_MESSAGES.get(label, "Unknown")
                self.signals.status_changed.emit(f"ALERT: {behavior}", StatusColor.RED)
                self.signals.violation_detected.emit(label, confidence)
                
                # Send to server
                if self.ws_client and self.ws_client.is_connected:
                    self.ws_client.send_violation(label, confidence)
            else:
                self.signals.status_changed.emit("Normal", StatusColor.GREEN)
            
            time.sleep(0.033)  # ~30 FPS
        
        # Cleanup
        cap.release()
        if self.detector:
            self.detector.release()
    
    def stop(self):
        """Stop the proctoring engine"""
        self.running = False
    
    def get_stats(self):
        """Get current statistics"""
        detection_rate = (self.faces_detected / self.total_frames * 100) if self.total_frames > 0 else 0
        return {
            "total_frames": self.total_frames,
            "faces_detected": self.faces_detected,
            "detection_rate": detection_rate,
            "violations": self.violations_count
        }


# ==================== STATUS DIALOG ====================

class StatusDialog(QDialog):
    """Status window showing detailed information"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FocusGuard Status")
        self.setFixedSize(300, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QPushButton {
                background-color: #0f3460;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1a4a7a;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        self.title = QLabel("FocusGuard Proctoring")
        self.title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.title.setStyleSheet("color: #00d4ff;")
        layout.addWidget(self.title)
        
        self.status_label = QLabel("Status: Initializing...")
        layout.addWidget(self.status_label)
        
        self.connection_label = QLabel("Server: Disconnected")
        layout.addWidget(self.connection_label)
        
        self.stats_label = QLabel("Frames: 0 | Violations: 0")
        layout.addWidget(self.stats_label)
        
        layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.hide)
        layout.addWidget(close_btn)
    
    def update_status(self, status: str, color: str):
        self.status_label.setText(f"Status: {status}")
        self.status_label.setStyleSheet(f"color: {color};")
    
    def update_connection(self, connected: bool):
        if connected:
            self.connection_label.setText("Server: Connected")
            self.connection_label.setStyleSheet("color: #00ff88;")
        else:
            self.connection_label.setText("Server: Disconnected")
            self.connection_label.setStyleSheet("color: #ff4444;")
    
    def update_stats(self, frames: int, violations: int):
        self.stats_label.setText(f"Frames: {frames} | Violations: {violations}")


# ==================== TRAY APPLICATION ====================

class TrayApp(QSystemTrayIcon):
    """
    System tray application for FocusGuard client
    Shows status icon and provides menu
    """
    
    def __init__(self, app: QApplication, student_id: str = "STUDENT"):
        super().__init__()
        
        self.app = app
        self.student_id = student_id
        self.violation_count = 0
        
        # Create signals
        self.signals = StatusSignals()
        self.signals.status_changed.connect(self.on_status_changed)
        self.signals.violation_detected.connect(self.on_violation_detected)
        
        # Status dialog
        self.status_dialog = StatusDialog()
        
        # Initialize WebSocket client
        server_url = f"ws://{Config.SERVER_HOST}:{Config.SERVER_PORT}/ws"
        self.ws_client = SyncWebSocketClient(
            server_url=server_url,
            student_id=student_id
        )
        
        # Initialize proctoring engine
        self.engine = ProctorEngine(
            self.signals,
            self.ws_client,
            Config.CAMERA_INDEX
        )
        
        # Setup tray
        self.setup_tray()
        
        # Start services
        self.start()
    
    def setup_tray(self):
        """Setup system tray icon and menu"""
        self.set_icon_color(StatusColor.GRAY)
        
        # Create menu
        menu = QMenu()
        
        # Student ID
        id_action = QAction(f"Student: {self.student_id}", menu)
        id_action.setEnabled(False)
        menu.addAction(id_action)
        
        # Status action
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
        
        # Show status window
        show_action = QAction("Show Status", menu)
        show_action.triggered.connect(self.show_status)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)
        self.setToolTip(f"FocusGuard - {self.student_id}")
        
        # Double-click shows status
        self.activated.connect(self.on_activated)
        
        self.show()
    
    def set_icon_color(self, color: str):
        """Create a colored circle icon"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Map color string to QColor
        if color == StatusColor.GREEN:
            qcolor = QColor(0, 200, 0)
        elif color == StatusColor.RED:
            qcolor = QColor(200, 0, 0)
        elif color == StatusColor.GRAY:
            qcolor = QColor(128, 128, 128)
        else:
            qcolor = QColor(color)
        
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
        
        # Update stats periodically
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(2000)
        
        # Start proctoring engine
        self.engine.start()
    
    def update_connection_status(self):
        """Update connection status in menu"""
        connected = self.ws_client.is_connected
        if connected:
            self.connection_action.setText("Server: Connected")
        else:
            self.connection_action.setText("Server: Disconnected")
        self.status_dialog.update_connection(connected)
    
    def update_stats(self):
        """Update statistics"""
        stats = self.engine.get_stats()
        self.status_dialog.update_stats(stats["total_frames"], stats["violations"])
    
    def on_status_changed(self, status: str, color: str):
        """Handle status change"""
        self.status_action.setText(f"Status: {status}")
        self.set_icon_color(color)
        self.status_dialog.update_status(status, color)
    
    def on_violation_detected(self, label: int, confidence: float):
        """Handle violation detection"""
        self.violation_count += 1
        self.violation_action.setText(f"Violations: {self.violation_count}")
        
        # Show notification
        behavior = VIOLATION_MESSAGES.get(label, "Unknown")
        self.showMessage(
            "FocusGuard Alert",
            f"Violation: {behavior}",
            QSystemTrayIcon.MessageIcon.Warning,
            2000
        )
    
    def on_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_status()
    
    def show_status(self):
        """Show status dialog"""
        self.status_dialog.show()
        self.status_dialog.raise_()
    
    def quit(self):
        """Clean shutdown"""
        self.engine.stop()
        self.ws_client.stop()
        self.connection_timer.stop()
        self.stats_timer.stop()
        self.app.quit()


# ==================== MAIN ====================

def run_tray_app(student_id: str = "STUDENT_001"):
    """Run the tray application"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    tray = TrayApp(app, student_id)
    
    return app.exec()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FocusGuard Tray App")
    parser.add_argument("--student-id", default="STUDENT_001")
    args = parser.parse_args()
    
    print("=" * 50)
    print("FocusGuard - Student Proctoring Client")
    print("=" * 50)
    print(f"Student ID: {args.student_id}")
    print("Look for the tray icon in system tray!")
    print("=" * 50)
    
    sys.exit(run_tray_app(args.student_id))
