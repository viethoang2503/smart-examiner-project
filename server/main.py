"""
FocusGuard Server - FastAPI WebSocket Backend
Handles multiple student connections and violation tracking
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.constants import Config, MessageType, VIOLATION_MESSAGES
from server.auth_routes import router as auth_router, init_auth
from server.exam_routes import router as exam_router


# ==================== DATA MODELS ====================

@dataclass
class Violation:
    """Represents a single violation event"""
    timestamp: str
    behavior: int
    behavior_name: str
    confidence: float


@dataclass
class StudentSession:
    """Represents a connected student session"""
    student_id: str
    connected_at: str
    last_heartbeat: str
    is_online: bool = True
    violations: List[Violation] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "student_id": self.student_id,
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
            "is_online": self.is_online,
            "violation_count": len(self.violations),
            "violations": [asdict(v) for v in self.violations[-10:]]
        }


# ==================== CONNECTION MANAGER ====================

class ConnectionManager:
    """Manages WebSocket connections for multiple students"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.sessions: Dict[str, StudentSession] = {}
        self.dashboard_connections: Set[WebSocket] = set()
    
    async def connect_student(self, websocket: WebSocket, student_id: str):
        await websocket.accept()
        self.active_connections[student_id] = websocket
        
        now = datetime.now().isoformat()
        if student_id in self.sessions:
            self.sessions[student_id].is_online = True
            self.sessions[student_id].last_heartbeat = now
        else:
            self.sessions[student_id] = StudentSession(
                student_id=student_id,
                connected_at=now,
                last_heartbeat=now
            )
        
        print(f"[Server] Student connected: {student_id}")
        await self.broadcast_to_dashboards({
            "type": "student_connected",
            "student_id": student_id,
            "timestamp": now
        })
    
    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_connections.add(websocket)
        print(f"[Server] Dashboard connected. Total: {len(self.dashboard_connections)}")
    
    def disconnect_student(self, student_id: str):
        if student_id in self.active_connections:
            del self.active_connections[student_id]
        if student_id in self.sessions:
            self.sessions[student_id].is_online = False
        print(f"[Server] Student disconnected: {student_id}")
    
    def disconnect_dashboard(self, websocket: WebSocket):
        self.dashboard_connections.discard(websocket)
    
    async def handle_message(self, student_id: str, data: dict):
        msg_type = data.get("type")
        
        if msg_type == MessageType.HEARTBEAT:
            if student_id in self.sessions:
                self.sessions[student_id].last_heartbeat = datetime.now().isoformat()
        
        elif msg_type == MessageType.VIOLATION:
            violation = Violation(
                timestamp=data.get("timestamp", datetime.now().isoformat()),
                behavior=data.get("behavior", 0),
                behavior_name=data.get("behavior_name", "Unknown"),
                confidence=data.get("confidence", 0.0)
            )
            
            if student_id in self.sessions:
                self.sessions[student_id].violations.append(violation)
            
            print(f"[Server] Violation from {student_id}: {violation.behavior_name}")
            await self.broadcast_to_dashboards({
                "type": "violation",
                "student_id": student_id,
                "violation": asdict(violation)
            })
    
    async def broadcast_to_dashboards(self, message: dict):
        if not self.dashboard_connections:
            return
        
        disconnected = set()
        for ws in self.dashboard_connections:
            try:
                await ws.send_json(message)
            except:
                disconnected.add(ws)
        self.dashboard_connections -= disconnected
    
    def get_all_sessions(self) -> List[dict]:
        return [session.to_dict() for session in self.sessions.values()]
    
    def get_session(self, student_id: str) -> Optional[dict]:
        if student_id in self.sessions:
            return self.sessions[student_id].to_dict()
        return None
    
    def get_stats(self) -> dict:
        total_violations = sum(len(s.violations) for s in self.sessions.values())
        online_count = sum(1 for s in self.sessions.values() if s.is_online)
        return {
            "total_students": len(self.sessions),
            "online_students": online_count,
            "total_violations": total_violations,
            "dashboard_connections": len(self.dashboard_connections)
        }


# ==================== FASTAPI APP ====================

app = FastAPI(title="FocusGuard Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register auth routes
app.include_router(auth_router)
app.include_router(exam_router)

# Mount uploads directory for serving violation screenshots
from fastapi.staticfiles import StaticFiles
import os
uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

manager = ConnectionManager()


# ==================== WEBSOCKET ENDPOINTS ====================

@app.websocket("/ws")
async def websocket_student_endpoint(websocket: WebSocket):
    student_id = None
    try:
        await websocket.accept()
        first_msg = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        data = json.loads(first_msg)
        
        if data.get("type") != MessageType.CONNECT:
            await websocket.close(code=4001)
            return
        
        student_id = data.get("student_id", "UNKNOWN")
        manager.active_connections[student_id] = websocket
        now = datetime.now().isoformat()
        
        if student_id in manager.sessions:
            manager.sessions[student_id].is_online = True
            manager.sessions[student_id].last_heartbeat = now
        else:
            manager.sessions[student_id] = StudentSession(
                student_id=student_id,
                connected_at=now,
                last_heartbeat=now
            )
        
        print(f"[Server] Student connected: {student_id}")
        await manager.broadcast_to_dashboards({
            "type": "student_connected",
            "student_id": student_id,
            "timestamp": now
        })
        
        while True:
            text = await websocket.receive_text()
            data = json.loads(text)
            await manager.handle_message(student_id, data)
            
    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        await websocket.close(code=4002)
    except Exception as e:
        print(f"[Server] WebSocket error: {e}")
    finally:
        if student_id:
            manager.disconnect_student(student_id)
            await manager.broadcast_to_dashboards({
                "type": "student_disconnected",
                "student_id": student_id,
                "timestamp": datetime.now().isoformat()
            })


@app.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    await manager.connect_dashboard(websocket)
    try:
        await websocket.send_json({
            "type": "init",
            "sessions": manager.get_all_sessions(),
            "stats": manager.get_stats()
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_dashboard(websocket)


# ==================== REST API ====================

@app.get("/")
async def root():
    return {"name": "FocusGuard Server", "status": "running", "stats": manager.get_stats()}


@app.get("/api/students")
async def get_all_students():
    return {"students": manager.get_all_sessions(), "count": len(manager.sessions)}


@app.get("/api/students/{student_id}")
async def get_student(student_id: str):
    session = manager.get_session(student_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return session


@app.get("/api/stats")
async def get_stats():
    return manager.get_stats()


# ==================== DASHBOARD HTML ====================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>FocusGuard Dashboard</title>
    <style>
        body { font-family: Arial; margin: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #00d4ff; }
        .stats { display: flex; gap: 20px; margin-bottom: 20px; }
        .stat-card { background: #16213e; padding: 20px; border-radius: 10px; min-width: 150px; }
        .stat-value { font-size: 32px; font-weight: bold; color: #00d4ff; }
        .stat-label { color: #888; }
        .student-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
        .student-card { background: #16213e; padding: 15px; border-radius: 10px; border-left: 4px solid #00d4ff; }
        .student-card.offline { border-left-color: #888; opacity: 0.7; }
        .student-card.violation { border-left-color: #ff4444; animation: pulse 1s; }
        .student-id { font-weight: bold; font-size: 18px; }
        .online-badge { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
        .online-badge.online { background: #00ff88; }
        .online-badge.offline { background: #888; }
        .violation-count { color: #ff4444; font-weight: bold; }
        .violation-list { max-height: 150px; overflow-y: auto; font-size: 12px; margin-top: 10px; }
        .violation-item { background: #0f0f23; padding: 5px 10px; margin: 5px 0; border-radius: 5px; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h1 style="margin: 0;">FocusGuard Dashboard</h1>
        <div>
            <a href="/dashboard" style="color: #00d4ff; margin-right: 15px; text-decoration: none;">Dashboard</a>
            <a href="/admin" style="color: #888; margin-right: 15px; text-decoration: none;">Users</a>
            <a href="/exams" style="color: #ff9800; margin-right: 15px; text-decoration: none; font-weight: bold;">📝 Exams</a>
            <button onclick="logout()" style="background: #f44336; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer;">Logout</button>
        </div>
    </div>
    <div class="stats">
        <div class="stat-card"><div class="stat-value" id="total-students">0</div><div class="stat-label">Total Students</div></div>
        <div class="stat-card"><div class="stat-value" id="online-students">0</div><div class="stat-label">Online</div></div>
        <div class="stat-card"><div class="stat-value" id="total-violations">0</div><div class="stat-label">Violations</div></div>
    </div>
    <h2>Students</h2>
    <div class="student-grid" id="students"></div>
    <script>
        const ws = new WebSocket(`ws://${location.host}/ws/dashboard`);
        let sessions = {};
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'init') {
                data.sessions.forEach(s => sessions[s.student_id] = s);
                updateStats(data.stats);
                renderStudents();
            } else if (data.type === 'student_connected') {
                sessions[data.student_id] = sessions[data.student_id] || {student_id: data.student_id, is_online: true, violation_count: 0, violations: []};
                sessions[data.student_id].is_online = true;
                renderStudents();
                fetchStats();
            } else if (data.type === 'student_disconnected') {
                if (sessions[data.student_id]) sessions[data.student_id].is_online = false;
                renderStudents();
                fetchStats();
            } else if (data.type === 'violation') {
                if (sessions[data.student_id]) {
                    sessions[data.student_id].violations.unshift(data.violation);
                    sessions[data.student_id].violation_count++;
                    renderStudents();
                    highlightViolation(data.student_id);
                    fetchStats();
                }
            }
        };
        function updateStats(s) {
            document.getElementById('total-students').textContent = s.total_students;
            document.getElementById('online-students').textContent = s.online_students;
            document.getElementById('total-violations').textContent = s.total_violations;
        }
        function fetchStats() { fetch('/api/stats').then(r => r.json()).then(updateStats); }
        function renderStudents() {
            document.getElementById('students').innerHTML = Object.values(sessions).map(s => `
                <div class="student-card ${s.is_online ? '' : 'offline'}" id="student-${s.student_id}">
                    <div><span class="online-badge ${s.is_online ? 'online' : 'offline'}"></span><span class="student-id">${s.student_id}</span></div>
                    <div>Violations: <span class="violation-count">${s.violation_count || 0}</span></div>
                    <div class="violation-list">${(s.violations || []).slice(0, 5).map(v => `<div class="violation-item">${v.behavior_name} - ${new Date(v.timestamp).toLocaleTimeString()}</div>`).join('')}</div>
                </div>
            `).join('');
        }
        function highlightViolation(id) {
            const c = document.getElementById('student-' + id);
            if (c) { c.classList.add('violation'); setTimeout(() => c.classList.remove('violation'), 2000); }
        }
        function logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
        }
    </script>
</body>
</html>
"""

# ==================== LOGIN PAGE HTML ====================

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>FocusGuard - Login</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-box {
            background: #16213e;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 400px;
        }
        h1 { color: #00d4ff; text-align: center; margin-bottom: 10px; }
        .subtitle { color: #888; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { color: #ccc; display: block; margin-bottom: 8px; font-size: 14px; }
        input { 
            width: 100%;
            padding: 12px 15px;
            background: #0f3460;
            border: 2px solid #0f3460;
            border-radius: 8px;
            color: white;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }
        input:focus { border-color: #00d4ff; }
        .error { 
            background: #ff444420;
            color: #ff4444;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
            text-align: center;
        }
        button {
            width: 100%;
            padding: 14px;
            background: #00d4ff;
            color: #1a1a2e;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover { background: #00a8cc; }
        button:disabled { background: #555; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>FocusGuard</h1>
        <p class="subtitle">AI Proctoring System</p>
        
        <div class="error" id="error"></div>
        
        <form id="loginForm">
            <div class="form-group">
                <label>Username</label>
                <input type="text" id="username" placeholder="Enter username" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" id="password" placeholder="Enter password" required>
            </div>
            <button type="submit" id="loginBtn">Login</button>
        </form>
    </div>
    
    <script>
        document.getElementById('loginForm').onsubmit = async (e) => {
            e.preventDefault();
            const btn = document.getElementById('loginBtn');
            const error = document.getElementById('error');
            
            btn.disabled = true;
            btn.textContent = 'Logging in...';
            error.style.display = 'none';
            
            try {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        username: document.getElementById('username').value,
                        password: document.getElementById('password').value
                    })
                });
                
                if (res.ok) {
                    const data = await res.json();
                    localStorage.setItem('token', data.access_token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                    
                    // Redirect based on role
                    if (data.user.role === 'admin' || data.user.role === 'teacher') {
                        window.location.href = '/dashboard';
                    } else {
                        error.textContent = 'Students please use the client app';
                        error.style.display = 'block';
                    }
                } else {
                    error.textContent = 'Invalid username or password';
                    error.style.display = 'block';
                }
            } catch (err) {
                error.textContent = 'Connection error';
                error.style.display = 'block';
            }
            
            btn.disabled = false;
            btn.textContent = 'Login';
        };
        
        // Clear any existing session - require fresh login each time
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    </script>
</body>
</html>
"""

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return LOGIN_HTML


# ==================== ADMIN PANEL HTML ====================

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>FocusGuard - Admin Panel</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial; background: #1a1a2e; color: #eee; padding: 20px; }
        h1 { color: #00d4ff; margin-bottom: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .nav { display: flex; gap: 15px; }
        .nav a { color: #00d4ff; text-decoration: none; padding: 8px 15px; border-radius: 5px; }
        .nav a:hover { background: #16213e; }
        .card { background: #16213e; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #0f3460; }
        th { color: #00d4ff; }
        .badge { padding: 4px 10px; border-radius: 15px; font-size: 12px; }
        .badge-admin { background: #ff9800; color: #000; }
        .badge-teacher { background: #2196f3; }
        .badge-student { background: #4caf50; }
        .badge-active { background: #4caf5030; color: #4caf50; }
        .badge-inactive { background: #f4433630; color: #f44336; }
        .btn { padding: 6px 12px; border: none; border-radius: 5px; cursor: pointer; margin: 2px; }
        .btn-danger { background: #f44336; color: white; }
        .btn-primary { background: #00d4ff; color: #1a1a2e; }
        .btn-secondary { background: #555; color: white; }
        .btn:hover { opacity: 0.8; }
        .form-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 15px; }
        input, select { width: 100%; padding: 10px; background: #0f3460; border: 2px solid #0f3460; border-radius: 5px; color: white; }
        input:focus, select:focus { border-color: #00d4ff; outline: none; }
        .user-info { color: #888; font-size: 14px; }
        .logout-btn { background: #f44336; color: white; padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Admin Panel</h1>
        <div style="display: flex; align-items: center; gap: 15px;">
            <span class="user-info">Logged in as: <strong id="currentUser">-</strong></span>
            <button class="logout-btn" onclick="logout()">Logout</button>
        </div>
    </div>
    
    <div class="nav">
        <a href="/dashboard">Dashboard</a>
        <a href="/admin" style="background: #16213e;">User Management</a>
        <a href="/exams" style="color: #ff9800;">📝 Exams</a>
    </div>
    
    <!-- Create User Form -->
    <div class="card">
        <h3 style="margin-bottom: 15px; color: #00d4ff;">Create New User</h3>
        <form id="createForm">
            <div class="form-row">
                <input type="text" id="username" placeholder="Username" required>
                <input type="password" id="password" placeholder="Password" required>
                <input type="text" id="fullName" placeholder="Full Name" required>
            </div>
            <div class="form-row">
                <select id="role">
                    <option value="student">Student</option>
                    <option value="teacher">Teacher</option>
                    <option value="admin">Admin</option>
                </select>
                <input type="text" id="className" placeholder="Class (optional)">
                <input type="text" id="studentId" placeholder="Student ID (optional)">
            </div>
            <button type="submit" class="btn btn-primary">Create User</button>
        </form>
    </div>
    
    <!-- Users Table -->
    <div class="card">
        <h3 style="margin-bottom: 15px; color: #00d4ff;">All Users</h3>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Full Name</th>
                    <th>Role</th>
                    <th>Class</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="usersTable"></tbody>
        </table>
    </div>
    
    <script>
        const token = localStorage.getItem('token');
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        
        if (!token || user.role !== 'admin') {
            alert('Admin access required');
            window.location.href = '/login';
        }
        
        document.getElementById('currentUser').textContent = user.full_name || user.username;
        
        // Fetch users
        async function loadUsers() {
            const res = await fetch('/api/auth/users', {
                headers: {'Authorization': 'Bearer ' + token}
            });
            const users = await res.json();
            
            document.getElementById('usersTable').innerHTML = users.map(u => `
                <tr>
                    <td>${u.id}</td>
                    <td>${u.username}</td>
                    <td>${u.full_name}</td>
                    <td><span class="badge badge-${u.role}">${u.role}</span></td>
                    <td>${u.class_name || '-'}</td>
                    <td><span class="badge ${u.is_active ? 'badge-active' : 'badge-inactive'}">${u.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td>
                        <button class="btn btn-secondary" onclick="toggleUser(${u.id})">${u.is_active ? 'Disable' : 'Enable'}</button>
                        <button class="btn btn-danger" onclick="deleteUser(${u.id}, '${u.username}')">Delete</button>
                    </td>
                </tr>
            `).join('');
        }
        
        loadUsers();
        
        // Create user
        document.getElementById('createForm').onsubmit = async (e) => {
            e.preventDefault();
            const res = await fetch('/api/auth/users', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: document.getElementById('username').value,
                    password: document.getElementById('password').value,
                    full_name: document.getElementById('fullName').value,
                    role: document.getElementById('role').value,
                    class_name: document.getElementById('className').value || null,
                    student_id: document.getElementById('studentId').value || null
                })
            });
            
            if (res.ok) {
                alert('User created!');
                document.getElementById('createForm').reset();
                loadUsers();
            } else {
                const err = await res.json();
                alert(err.detail || 'Error creating user');
            }
        };
        
        // Toggle user active status
        async function toggleUser(id) {
            await fetch(`/api/auth/users/${id}/toggle-active`, {
                method: 'PUT',
                headers: {'Authorization': 'Bearer ' + token}
            });
            loadUsers();
        }
        
        // Delete user
        async function deleteUser(id, username) {
            if (!confirm(`Delete user "${username}"?`)) return;
            await fetch(`/api/auth/users/${id}`, {
                method: 'DELETE',
                headers: {'Authorization': 'Bearer ' + token}
            });
            loadUsers();
        }
        
        // Logout
        function logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
        }
    </script>
</body>
</html>
"""

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    return ADMIN_HTML


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


# ==================== EXAM MANAGEMENT PAGE ====================

EXAMS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>FocusGuard - Exam Management</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial; background: #1a1a2e; color: #eee; padding: 20px; }
        h1, h2, h3 { color: #00d4ff; margin-bottom: 15px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .nav { display: flex; gap: 15px; margin-bottom: 20px; }
        .nav a { color: #00d4ff; text-decoration: none; padding: 8px 15px; border-radius: 5px; }
        .nav a:hover, .nav a.active { background: #16213e; }
        .card { background: #16213e; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .grid-2 { display: grid; grid-template-columns: 1fr 2fr; gap: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #0f3460; }
        th { color: #00d4ff; }
        .badge { padding: 4px 10px; border-radius: 15px; font-size: 12px; }
        .badge-pending { background: #ff980030; color: #ff9800; }
        .badge-active { background: #4caf5030; color: #4caf50; }
        .badge-ended { background: #9e9e9e30; color: #9e9e9e; }
        .badge-flagged { background: #f4433630; color: #f44336; }
        .btn { padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; margin: 2px; font-size: 13px; }
        .btn-primary { background: #00d4ff; color: #1a1a2e; }
        .btn-success { background: #4caf50; color: white; }
        .btn-danger { background: #f44336; color: white; }
        .btn-secondary { background: #555; color: white; }
        .btn:hover { opacity: 0.8; }
        input, select { width: 100%; padding: 10px; background: #0f3460; border: 2px solid #0f3460; border-radius: 5px; color: white; margin-bottom: 10px; }
        input:focus, select:focus { border-color: #00d4ff; outline: none; }
        .exam-code { font-size: 28px; font-weight: bold; color: #00d4ff; letter-spacing: 3px; }
        .timer { font-size: 32px; font-weight: bold; text-align: center; padding: 15px; border-radius: 10px; }
        .timer.warning { background: #ff980030; color: #ff9800; }
        .timer.danger { background: #f4433630; color: #f44336; }
        .timer.normal { background: #4caf5030; color: #4caf50; }
        .stats { display: flex; gap: 15px; margin-bottom: 15px; }
        .stat { background: #0f3460; padding: 15px; border-radius: 8px; text-align: center; flex: 1; }
        .stat-value { font-size: 24px; font-weight: bold; color: #00d4ff; }
        .logout-btn { background: #f44336; color: white; padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; }
        .participant-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
        .participant-card { background: #0f3460; padding: 12px; border-radius: 8px; border-left: 3px solid; }
        .participant-card.online { border-color: #4caf50; }
        .participant-card.offline { border-color: #9e9e9e; opacity: 0.7; }
        .participant-card.flagged { border-color: #f44336; background: #f4433615; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Exam Management</h1>
        <div style="display: flex; align-items: center; gap: 15px;">
            <span id="currentUser">-</span>
            <button class="logout-btn" onclick="logout()">Logout</button>
        </div>
    </div>
    
    <div class="nav">
        <a href="/dashboard">Dashboard</a>
        <a href="/admin">Users</a>
        <a href="/exams" class="active">Exams</a>
    </div>
    
    <div class="grid-2">
        <!-- Left: Create Form -->
        <div class="card">
            <h3>Create New Exam</h3>
            <form id="createForm">
                <div style="margin-bottom: 12px;">
                    <label style="display: block; color: #888; font-size: 12px; margin-bottom: 4px;">📝 Exam Name</label>
                    <input type="text" id="examName" placeholder="e.g. Midterm Math" required style="width: 100%;">
                </div>
                <div style="margin-bottom: 12px;">
                    <label style="display: block; color: #888; font-size: 12px; margin-bottom: 4px;">📅 Exam Date</label>
                    <input type="date" id="examDate" required style="width: 100%;">
                </div>
                <div style="margin-bottom: 12px;">
                    <label style="display: block; color: #888; font-size: 12px; margin-bottom: 4px;">⏱️ Duration (minutes)</label>
                    <input type="number" id="duration" placeholder="60" value="60" min="1" required style="width: 100%;">
                </div>
                <div style="margin-bottom: 12px;">
                    <label style="display: block; color: #888; font-size: 12px; margin-bottom: 4px;">⚠️ Max Violations (auto-flag if exceeded)</label>
                    <input type="number" id="maxViolations" placeholder="5" value="5" min="1" required style="width: 100%;">
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">Create Exam</button>
            </form>
        </div>
        
        <!-- Right: Exams List -->
        <div class="card">
            <h3>Your Exams</h3>
            <table>
                <thead>
                    <tr>
                        <th>Code</th>
                        <th>Name</th>
                        <th>Status</th>
                        <th>Students</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="examsTable"></tbody>
            </table>
        </div>
    </div>
    
    <!-- Exam Detail Modal -->
    <div id="examDetail" class="hidden">
        <div class="card">
            <div class="header">
                <div>
                    <h2 id="detailName">-</h2>
                    <div class="exam-code" id="detailCode">-</div>
                </div>
                <button class="btn btn-secondary" onclick="hideDetail()">← Back</button>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-value" id="detailOnline">0</div>
                    <div>Online</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="detailTotal">0</div>
                    <div>Total</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="detailFlagged">0</div>
                    <div>Flagged</div>
                </div>
            </div>
            
            <div class="timer normal" id="countdown">--:--</div>
            
            <div style="margin: 15px 0; text-align: center;">
                <button class="btn btn-success" id="startBtn" onclick="startExam()">▶ Start Exam</button>
                <button class="btn btn-danger" id="endBtn" onclick="endExam()">⬛ End Exam</button>
            </div>
            
            <h3>Participants</h3>
            <div class="participant-grid" id="participants"></div>
        </div>
    </div>
    
    <script>
        const token = localStorage.getItem('token');
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        
        if (!token || (user.role !== 'admin' && user.role !== 'teacher')) {
            alert('Teacher/Admin access required');
            window.location.href = '/login';
        }
        
        document.getElementById('currentUser').textContent = user.full_name;
        
        let currentExam = null;
        let timerInterval = null;
        
        // Load exams
        async function loadExams() {
            const res = await fetch('/api/exams', {
                headers: {'Authorization': 'Bearer ' + token}
            });
            const exams = await res.json();
            
            document.getElementById('examsTable').innerHTML = exams.map(e => `
                <tr>
                    <td><strong>${e.exam_code}</strong></td>
                    <td>${e.exam_name}</td>
                    <td><span class="badge badge-${e.status}">${e.status}</span></td>
                    <td>${e.online_count}/${e.participant_count}</td>
                    <td>
                        <button class="btn btn-primary" onclick="showDetail('${e.exam_code}')">View</button>
                    </td>
                </tr>
            `).join('') || '<tr><td colspan="5" style="text-align:center; color:#888;">No exams yet</td></tr>';
        }
        
        loadExams();
        
        // Create exam
        document.getElementById('createForm').onsubmit = async (e) => {
            e.preventDefault();
            const res = await fetch('/api/exams', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    exam_name: document.getElementById('examName').value,
                    exam_date: document.getElementById('examDate').value || null,
                    duration_minutes: parseInt(document.getElementById('duration').value),
                    max_violations: parseInt(document.getElementById('maxViolations').value)
                })
            });
            
            if (res.ok) {
                const data = await res.json();
                alert('Exam created! Code: ' + data.exam_code);
                document.getElementById('createForm').reset();
                loadExams();
            }
        };
        
        // Show exam detail
        async function showDetail(code) {
            const res = await fetch(`/api/exams/${code}`, {
                headers: {'Authorization': 'Bearer ' + token}
            });
            currentExam = await res.json();
            
            document.getElementById('detailName').textContent = currentExam.exam_name;
            document.getElementById('detailCode').textContent = currentExam.exam_code;
            document.getElementById('detailTotal').textContent = currentExam.participant_count;
            document.getElementById('detailOnline').textContent = currentExam.online_count;
            
            document.getElementById('startBtn').style.display = currentExam.status === 'pending' ? 'inline-block' : 'none';
            document.getElementById('endBtn').style.display = currentExam.status === 'active' ? 'inline-block' : 'none';
            
            document.getElementById('examDetail').classList.remove('hidden');
            document.querySelector('.grid-2').classList.add('hidden');
            
            loadParticipants();
            startTimer();
        }
        
        function hideDetail() {
            document.getElementById('examDetail').classList.add('hidden');
            document.querySelector('.grid-2').classList.remove('hidden');
            if (timerInterval) clearInterval(timerInterval);
            loadExams();
        }
        
        // Load participants
        async function loadParticipants() {
            if (!currentExam) return;
            
            const res = await fetch(`/api/exams/${currentExam.exam_code}/participants`, {
                headers: {'Authorization': 'Bearer ' + token}
            });
            const participants = await res.json();
            
            document.getElementById('detailFlagged').textContent = participants.filter(p => p.is_flagged).length;
            document.getElementById('detailOnline').textContent = participants.filter(p => p.is_online).length;
            document.getElementById('detailTotal').textContent = participants.length;
            
            document.getElementById('participants').innerHTML = participants.map(p => `
                <div class="participant-card ${p.is_flagged ? 'flagged' : (p.is_online ? 'online' : 'offline')}" style="cursor: pointer;" onclick="viewViolations(${p.user_id}, '${p.full_name}')">
                    <strong>${p.full_name}</strong>
                    <div style="font-size: 12px; color: #888;">${p.class_name || ''}</div>
                    <div style="margin-top: 5px;">
                        Violations: <strong style="color: ${p.is_flagged ? '#f44336' : '#fff'}">${p.violation_count}</strong>
                        ${p.is_flagged ? '<span class="badge badge-flagged">FLAGGED</span>' : ''}
                    </div>
                    <button class="btn btn-primary" style="margin-top: 8px; padding: 5px 10px; font-size: 11px;" onclick="event.stopPropagation(); viewViolations(${p.user_id}, '${p.full_name}')">📷 View Report</button>
                </div>
            `).join('') || '<p style="color: #888;">No participants yet</p>';
        }
        
        // Timer
        function startTimer() {
            if (timerInterval) clearInterval(timerInterval);
            
            const update = () => {
                const timer = document.getElementById('countdown');
                
                if (!currentExam || currentExam.status !== 'active' || !currentExam.started_at) {
                    timer.textContent = currentExam?.status === 'pending' ? 'Waiting to start' : 'Exam ended';
                    timer.className = 'timer ' + (currentExam?.status === 'ended' ? 'danger' : 'normal');
                    return;
                }
                
                const started = new Date(currentExam.started_at);
                const endTime = new Date(started.getTime() + currentExam.duration_minutes * 60 * 1000);
                const now = new Date();
                const remaining = Math.max(0, Math.floor((endTime - now) / 1000));
                
                const mins = Math.floor(remaining / 60);
                const secs = remaining % 60;
                timer.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                
                if (remaining === 0) {
                    timer.className = 'timer danger';
                    timer.textContent = 'TIME UP';
                } else if (remaining < 300) {
                    timer.className = 'timer danger';
                } else if (remaining < 600) {
                    timer.className = 'timer warning';
                } else {
                    timer.className = 'timer normal';
                }
            };
            
            update();
            timerInterval = setInterval(() => {
                update();
                loadParticipants();
            }, 5000);
        }
        
        // Start exam
        async function startExam() {
            if (!confirm('Start this exam?')) return;
            
            await fetch(`/api/exams/${currentExam.exam_code}/start`, {
                method: 'POST',
                headers: {'Authorization': 'Bearer ' + token}
            });
            
            showDetail(currentExam.exam_code);
        }
        
        // End exam
        async function endExam() {
            if (!confirm('End this exam? This cannot be undone.')) return;
            
            await fetch(`/api/exams/${currentExam.exam_code}/end`, {
                method: 'POST',
                headers: {'Authorization': 'Bearer ' + token}
            });
            
            showDetail(currentExam.exam_code);
        }
        
        // View violations report for a student
        async function viewViolations(userId, userName) {
            const res = await fetch(`/api/exams/${currentExam.exam_code}/violations?user_id=${userId}`, {
                headers: {'Authorization': 'Bearer ' + token}
            });
            const violations = await res.json();
            
            let html = `<h2>Violations Report: ${userName}</h2>
                <p>Exam: ${currentExam.exam_name} (${currentExam.exam_code})</p>
                <p>Total Violations: ${violations.length}</p>
                <button class="btn btn-secondary" onclick="loadParticipants()">← Back</button>
                <hr style="border-color: #333; margin: 15px 0;">`;
            
            if (violations.length === 0) {
                html += '<p style="color: #888;">No violations recorded</p>';
            } else {
                html += '<div style="display: grid; gap: 15px;">';
                violations.forEach(v => {
                    const time = new Date(v.timestamp).toLocaleString();
                    html += `<div style="background: #0f3460; padding: 15px; border-radius: 8px; border-left: 3px solid #f44336;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                            <strong style="color: #f44336;">${v.behavior_name}</strong>
                            <span style="color: #888; font-size: 12px;">${time}</span>
                        </div>
                        <div style="font-size: 12px; color: #888;">Confidence: ${parseFloat(v.confidence).toFixed(2)}</div>
                        ${v.screenshot_path ? `<img src="${v.screenshot_path}" style="max-width: 100%; margin-top: 10px; border-radius: 5px; border: 2px solid #f44336;">` : '<div style="color: #666; font-size: 12px; margin-top: 5px;">No screenshot</div>'}
                    </div>`;
                });
                html += '</div>';
            }
            
            document.getElementById('participants').innerHTML = html;
        }
        
        function logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
        }
    </script>
</body>
</html>
"""

@app.get("/exams", response_class=HTMLResponse)
async def exams_page():
    return EXAMS_HTML

def main():
    import webbrowser
    import threading
    
    print("=" * 60)
    print("FocusGuard Server")
    print("=" * 60)
    
    # Initialize database and create default admin
    print("Initializing database...")
    init_auth()
    
    print(f"Starting on http://{Config.SERVER_HOST}:{Config.SERVER_PORT}")
    print(f"Login: http://localhost:{Config.SERVER_PORT}/login")
    print(f"Dashboard: http://localhost:{Config.SERVER_PORT}/dashboard")
    print("=" * 60)
    
    # Auto-open browser after 2 seconds
    def open_browser():
        import time
        time.sleep(2)
        webbrowser.open(f"http://localhost:{Config.SERVER_PORT}/login")
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run(app, host=Config.SERVER_HOST, port=Config.SERVER_PORT, log_level="info")


if __name__ == "__main__":
    main()
