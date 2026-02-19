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
from server.config import settings
from server.auth_routes import router as auth_router, init_auth
from server.exam_routes import router as exam_router
from server.report_routes import router as report_router


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

# CORS: Load allowed origins from .env config
cors_origins = settings.CORS_ORIGINS
if cors_origins == ["*"] and not settings.DEBUG:
    print("[Server] ⚠️  WARNING: CORS_ORIGINS is set to '*' in non-debug mode!")
    print("[Server] ⚠️  Please set specific origins in .env for production.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register auth routes
app.include_router(auth_router)
app.include_router(exam_router)
app.include_router(report_router)

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


# ==================== TEMPLATE RENDERING ====================

from fastapi.templating import Jinja2Templates
from fastapi import Request
from pathlib import Path

# Setup Jinja2 templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/exams", response_class=HTMLResponse)
async def exams_page(request: Request):
    return templates.TemplateResponse("exams.html", {"request": request})



def main():
    import webbrowser
    import threading
    
    print("=" * 60)
    print("FocusGuard Server")
    print("=" * 60)
    print(f"[Config] {settings}")
    
    # Initialize database and create default admin
    print("Initializing database...")
    init_auth()
    
    host = settings.SERVER_HOST
    port = settings.SERVER_PORT
    
    print(f"Starting on http://{host}:{port}")
    print(f"Login: http://localhost:{port}/login")
    print(f"Dashboard: http://localhost:{port}/dashboard")
    print("=" * 60)
    
    # Auto-open browser after 2 seconds
    def open_browser():
        import time
        time.sleep(2)
        webbrowser.open(f"http://localhost:{port}/login")
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()

