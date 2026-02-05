"""
FocusGuard - Teacher Dashboard GUI
PyQt6-based dashboard for monitoring students in real-time
"""

import sys
import os
import json
import asyncio
import threading
from datetime import datetime
from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QFrame, QScrollArea, QPushButton,
    QStatusBar, QMenuBar, QMenu, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QColor, QPalette, QAction

import websockets

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.constants import Config, StatusColor, VIOLATION_MESSAGES


# ==================== STYLES ====================

DARK_STYLE = """
QMainWindow {
    background-color: #1a1a2e;
}
QWidget {
    background-color: #1a1a2e;
    color: #ffffff;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QLabel {
    color: #ffffff;
}
QFrame#student_card {
    background-color: #16213e;
    border-radius: 10px;
    border: 2px solid #0f3460;
    padding: 10px;
}
QFrame#student_card[status="online"] {
    border-left: 4px solid #00ff88;
}
QFrame#student_card[status="offline"] {
    border-left: 4px solid #888888;
    opacity: 0.7;
}
QFrame#student_card[status="violation"] {
    border-left: 4px solid #ff4444;
    border: 2px solid #ff4444;
}
QFrame#stat_card {
    background-color: #16213e;
    border-radius: 10px;
    padding: 15px;
    min-width: 120px;
}
QPushButton {
    background-color: #0f3460;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 5px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1a4a7a;
}
QPushButton:pressed {
    background-color: #0a2540;
}
QScrollArea {
    border: none;
}
QStatusBar {
    background-color: #0f0f23;
    color: #888888;
}
QMenuBar {
    background-color: #0f0f23;
    color: white;
}
QMenuBar::item:selected {
    background-color: #16213e;
}
QMenu {
    background-color: #16213e;
    color: white;
}
QMenu::item:selected {
    background-color: #0f3460;
}
"""


# ==================== WEBSOCKET WORKER ====================

class WebSocketSignals(QObject):
    """Signals for WebSocket events"""
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    student_connected = pyqtSignal(str, str)  # student_id, timestamp
    student_disconnected = pyqtSignal(str)  # student_id
    violation_received = pyqtSignal(str, dict)  # student_id, violation_data
    init_data = pyqtSignal(list, dict)  # sessions, stats


class WebSocketWorker(QThread):
    """Background thread for WebSocket connection"""
    
    def __init__(self, server_url: str):
        super().__init__()
        self.server_url = server_url
        self.signals = WebSocketSignals()
        self.running = False
        self.websocket = None
    
    async def connect_and_listen(self):
        """Connect to server and listen for messages"""
        while self.running:
            try:
                async with websockets.connect(self.server_url) as ws:
                    self.websocket = ws
                    self.signals.connected.emit()
                    
                    async for message in ws:
                        if not self.running:
                            break
                        
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == "init":
                            self.signals.init_data.emit(
                                data.get("sessions", []),
                                data.get("stats", {})
                            )
                        elif msg_type == "student_connected":
                            self.signals.student_connected.emit(
                                data.get("student_id"),
                                data.get("timestamp")
                            )
                        elif msg_type == "student_disconnected":
                            self.signals.student_disconnected.emit(
                                data.get("student_id")
                            )
                        elif msg_type == "violation":
                            self.signals.violation_received.emit(
                                data.get("student_id"),
                                data.get("violation", {})
                            )
                            
            except Exception as e:
                print(f"[Dashboard] WebSocket error: {e}")
                self.signals.disconnected.emit()
                await asyncio.sleep(3)  # Reconnect delay
    
    def run(self):
        """Run the WebSocket event loop"""
        self.running = True
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.connect_and_listen())
    
    def stop(self):
        """Stop the worker"""
        self.running = False


# ==================== STUDENT CARD WIDGET ====================

class StudentCard(QFrame):
    """Widget representing a single student"""
    
    def __init__(self, student_id: str, parent=None):
        super().__init__(parent)
        self.student_id = student_id
        self.is_online = False
        self.violation_count = 0
        self.violations = []
        
        self.setObjectName("student_card")
        self.setProperty("status", "offline")
        self.setMinimumSize(250, 150)
        self.setMaximumSize(350, 200)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Header with status indicator
        header = QHBoxLayout()
        
        # Status dot
        self.status_dot = QLabel("●")
        self.status_dot.setFont(QFont("Arial", 16))
        self.status_dot.setStyleSheet("color: #888888;")
        header.addWidget(self.status_dot)
        
        # Student ID
        self.id_label = QLabel(self.student_id)
        self.id_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.addWidget(self.id_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        # Status text
        self.status_label = QLabel("Offline")
        self.status_label.setStyleSheet("color: #888888; font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # Violation count
        self.violation_label = QLabel("Violations: 0")
        self.violation_label.setStyleSheet("color: #ff4444; font-weight: bold;")
        layout.addWidget(self.violation_label)
        
        # Last violation
        self.last_violation_label = QLabel("")
        self.last_violation_label.setStyleSheet("color: #ffaa00; font-size: 11px;")
        self.last_violation_label.setWordWrap(True)
        layout.addWidget(self.last_violation_label)
        
        layout.addStretch()
    
    def set_online(self, online: bool):
        self.is_online = online
        if online:
            self.status_dot.setStyleSheet("color: #00ff88;")
            self.status_label.setText("Online - Monitoring")
            self.status_label.setStyleSheet("color: #00ff88; font-size: 12px;")
            self.setProperty("status", "online")
        else:
            self.status_dot.setStyleSheet("color: #888888;")
            self.status_label.setText("Offline")
            self.status_label.setStyleSheet("color: #888888; font-size: 12px;")
            self.setProperty("status", "offline")
        
        # Force style update
        self.style().unpolish(self)
        self.style().polish(self)
    
    def add_violation(self, violation: dict):
        self.violation_count += 1
        self.violations.insert(0, violation)
        
        self.violation_label.setText(f"Violations: {self.violation_count}")
        
        behavior = violation.get("behavior_name", "Unknown")
        timestamp = violation.get("timestamp", "")
        try:
            time_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
        except:
            time_str = timestamp
        
        self.last_violation_label.setText(f"Last: {behavior} at {time_str}")
        
        # Flash effect
        self.setProperty("status", "violation")
        self.style().unpolish(self)
        self.style().polish(self)
        
        # Reset after 2 seconds
        QTimer.singleShot(2000, self.reset_violation_style)
    
    def reset_violation_style(self):
        status = "online" if self.is_online else "offline"
        self.setProperty("status", status)
        self.style().unpolish(self)
        self.style().polish(self)


# ==================== STATS WIDGET ====================

class StatCard(QFrame):
    """Widget showing a single statistic"""
    
    def __init__(self, title: str, value: str = "0", color: str = "#00d4ff", parent=None):
        super().__init__(parent)
        self.setObjectName("stat_card")
        
        layout = QVBoxLayout(self)
        
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #888888; font-size: 12px;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
    
    def set_value(self, value):
        self.value_label.setText(str(value))


# ==================== MAIN DASHBOARD WINDOW ====================

class TeacherDashboard(QMainWindow):
    """Main dashboard window for teachers"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocusGuard - Teacher Dashboard")
        self.setMinimumSize(1200, 800)
        
        # Student cards dictionary
        self.student_cards: Dict[str, StudentCard] = {}
        
        # WebSocket worker
        self.ws_worker = None
        
        self.setup_ui()
        self.setup_menu()
        self.connect_to_server()
    
    def setup_ui(self):
        """Setup the main UI"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("🎓 FocusGuard Dashboard")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #00d4ff;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Connection status
        self.connection_label = QLabel("● Disconnected")
        self.connection_label.setStyleSheet("color: #ff4444; font-size: 14px;")
        header.addWidget(self.connection_label)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        header.addWidget(refresh_btn)
        
        main_layout.addLayout(header)
        
        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.total_students_stat = StatCard("Total Students", "0", "#00d4ff")
        stats_layout.addWidget(self.total_students_stat)
        
        self.online_students_stat = StatCard("Online", "0", "#00ff88")
        stats_layout.addWidget(self.online_students_stat)
        
        self.total_violations_stat = StatCard("Violations", "0", "#ff4444")
        stats_layout.addWidget(self.total_violations_stat)
        
        stats_layout.addStretch()
        main_layout.addLayout(stats_layout)
        
        # Students section header
        students_header = QLabel("Students")
        students_header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        main_layout.addWidget(students_header)
        
        # Scrollable student grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(self.grid_widget)
        main_layout.addWidget(scroll)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Starting...")
    
    def setup_menu(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_data)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        clear_action = QAction("Clear All Violations", self)
        clear_action.triggered.connect(self.clear_all_violations)
        view_menu.addAction(clear_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def connect_to_server(self):
        """Connect to WebSocket server"""
        server_url = f"ws://{Config.SERVER_HOST}:{Config.SERVER_PORT}/ws/dashboard"
        
        self.ws_worker = WebSocketWorker(server_url)
        self.ws_worker.signals.connected.connect(self.on_connected)
        self.ws_worker.signals.disconnected.connect(self.on_disconnected)
        self.ws_worker.signals.init_data.connect(self.on_init_data)
        self.ws_worker.signals.student_connected.connect(self.on_student_connected)
        self.ws_worker.signals.student_disconnected.connect(self.on_student_disconnected)
        self.ws_worker.signals.violation_received.connect(self.on_violation_received)
        
        self.ws_worker.start()
        self.status_bar.showMessage(f"Connecting to {server_url}...")
    
    def on_connected(self):
        """Handle connection established"""
        self.connection_label.setText("● Connected")
        self.connection_label.setStyleSheet("color: #00ff88; font-size: 14px;")
        self.status_bar.showMessage("Connected to server")
    
    def on_disconnected(self):
        """Handle connection lost"""
        self.connection_label.setText("● Disconnected")
        self.connection_label.setStyleSheet("color: #ff4444; font-size: 14px;")
        self.status_bar.showMessage("Disconnected - Reconnecting...")
    
    def on_init_data(self, sessions: list, stats: dict):
        """Handle initial data from server"""
        # Update stats
        self.total_students_stat.set_value(stats.get("total_students", 0))
        self.online_students_stat.set_value(stats.get("online_students", 0))
        self.total_violations_stat.set_value(stats.get("total_violations", 0))
        
        # Create student cards
        for session in sessions:
            student_id = session.get("student_id")
            if student_id:
                self.add_or_update_student(
                    student_id,
                    session.get("is_online", False),
                    session.get("violation_count", 0),
                    session.get("violations", [])
                )
        
        self.status_bar.showMessage(f"Loaded {len(sessions)} students")
    
    def on_student_connected(self, student_id: str, timestamp: str):
        """Handle student connection"""
        if student_id in self.student_cards:
            self.student_cards[student_id].set_online(True)
        else:
            self.add_or_update_student(student_id, True)
        
        # Update online count
        online_count = sum(1 for card in self.student_cards.values() if card.is_online)
        self.online_students_stat.set_value(online_count)
        self.total_students_stat.set_value(len(self.student_cards))
        
        self.status_bar.showMessage(f"Student connected: {student_id}")
    
    def on_student_disconnected(self, student_id: str):
        """Handle student disconnection"""
        if student_id in self.student_cards:
            self.student_cards[student_id].set_online(False)
        
        # Update online count
        online_count = sum(1 for card in self.student_cards.values() if card.is_online)
        self.online_students_stat.set_value(online_count)
        
        self.status_bar.showMessage(f"Student disconnected: {student_id}")
    
    def on_violation_received(self, student_id: str, violation: dict):
        """Handle violation alert"""
        if student_id in self.student_cards:
            self.student_cards[student_id].add_violation(violation)
        else:
            self.add_or_update_student(student_id, True)
            self.student_cards[student_id].add_violation(violation)
        
        # Update total violations
        total = sum(card.violation_count for card in self.student_cards.values())
        self.total_violations_stat.set_value(total)
        
        behavior = violation.get("behavior_name", "Unknown")
        self.status_bar.showMessage(f"⚠ Violation from {student_id}: {behavior}")
        
        # Play alert sound (optional - system beep)
        QApplication.beep()
    
    def add_or_update_student(
        self, 
        student_id: str, 
        is_online: bool = False,
        violation_count: int = 0,
        violations: list = None
    ):
        """Add a new student card or update existing"""
        if student_id not in self.student_cards:
            card = StudentCard(student_id)
            self.student_cards[student_id] = card
            
            # Calculate grid position
            count = len(self.student_cards) - 1
            cols = 4  # 4 columns
            row = count // cols
            col = count % cols
            
            self.grid_layout.addWidget(card, row, col)
        
        card = self.student_cards[student_id]
        card.set_online(is_online)
        card.violation_count = violation_count
        card.violation_label.setText(f"Violations: {violation_count}")
        
        if violations:
            card.violations = violations
            if violations:
                last = violations[0]
                behavior = last.get("behavior_name", "Unknown")
                card.last_violation_label.setText(f"Last: {behavior}")
    
    def refresh_data(self):
        """Refresh connection"""
        self.status_bar.showMessage("Refreshing...")
        if self.ws_worker:
            self.ws_worker.stop()
        self.connect_to_server()
    
    def clear_all_violations(self):
        """Clear all violation counts"""
        for card in self.student_cards.values():
            card.violation_count = 0
            card.violations = []
            card.violation_label.setText("Violations: 0")
            card.last_violation_label.setText("")
        
        self.total_violations_stat.set_value(0)
        self.status_bar.showMessage("All violations cleared")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About FocusGuard",
            "FocusGuard - AI Proctoring System\n\n"
            "Real-time student monitoring using Edge AI\n\n"
            "Version 1.0.0"
        )
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.ws_worker:
            self.ws_worker.stop()
            self.ws_worker.wait(2000)
        event.accept()


# ==================== MAIN ====================

def main():
    """Run the dashboard application"""
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    
    print("=" * 60)
    print("FocusGuard - Teacher Dashboard")
    print("=" * 60)
    print(f"Connecting to server at {Config.SERVER_HOST}:{Config.SERVER_PORT}")
    print("=" * 60)
    
    window = TeacherDashboard()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
