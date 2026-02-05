"""
WebSocket Client Module
Handles real-time communication with the server
Includes auto-reconnect and heartbeat mechanism
"""

import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from shared.constants import Config, MessageType, VIOLATION_MESSAGES


class WebSocketClient:
    """
    Async WebSocket client for FocusGuard
    Features:
    - Auto-reconnect on disconnect
    - Heartbeat mechanism (ping every 5s)
    - Send violation alerts
    """
    
    def __init__(
        self,
        server_url: str = None,
        student_id: str = "UNKNOWN",
        on_connect: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None,
        on_message: Optional[Callable] = None
    ):
        """
        Initialize WebSocket client
        
        Args:
            server_url: WebSocket server URL (ws://host:port/ws)
            student_id: Unique identifier for this student
            on_connect: Callback when connected
            on_disconnect: Callback when disconnected
            on_message: Callback when message received
        """
        if server_url is None:
            server_url = f"ws://{Config.SERVER_HOST}:{Config.SERVER_PORT}/ws"
        
        self.server_url = server_url
        self.student_id = student_id
        self.websocket = None
        self.is_connected = False
        self.should_run = False
        
        # Callbacks
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_message = on_message
        
        # Heartbeat
        self.heartbeat_interval = Config.HEARTBEAT_INTERVAL
        self.last_heartbeat = None
        
        # Reconnect settings
        self.reconnect_delay = Config.RECONNECT_DELAY
        self.max_reconnect_attempts = 10
        self.reconnect_attempts = 0
    
    async def connect(self):
        """Establish WebSocket connection"""
        try:
            self.websocket = await websockets.connect(
                self.server_url,
                ping_interval=20,
                ping_timeout=10
            )
            self.is_connected = True
            self.reconnect_attempts = 0
            
            print(f"[WS] Connected to {self.server_url}")
            
            # Send connect message
            await self.send_message({
                "type": MessageType.CONNECT,
                "student_id": self.student_id,
                "timestamp": datetime.now().isoformat()
            })
            
            if self.on_connect:
                self.on_connect()
                
            return True
            
        except Exception as e:
            print(f"[WS] Connection failed: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Close WebSocket connection"""
        self.should_run = False
        
        if self.websocket:
            try:
                await self.send_message({
                    "type": MessageType.DISCONNECT,
                    "student_id": self.student_id,
                    "timestamp": datetime.now().isoformat()
                })
                await self.websocket.close()
            except:
                pass
        
        self.is_connected = False
        self.websocket = None
        
        if self.on_disconnect:
            self.on_disconnect()
        
        print("[WS] Disconnected")
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send message to server
        
        Args:
            message: Dictionary to send as JSON
            
        Returns:
            True if sent successfully
        """
        if not self.is_connected or not self.websocket:
            return False
        
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"[WS] Send failed: {e}")
            return False
    
    async def send_violation(
        self, 
        behavior_label: int, 
        confidence: float
    ) -> bool:
        """
        Send violation alert to server
        
        Args:
            behavior_label: Behavior label (0-4)
            confidence: Detection confidence (0.0-1.0)
            
        Returns:
            True if sent successfully
        """
        message = {
            "type": MessageType.VIOLATION,
            "student_id": self.student_id,
            "behavior": behavior_label,
            "behavior_name": VIOLATION_MESSAGES.get(behavior_label, "Unknown"),
            "confidence": round(confidence, 2),
            "timestamp": datetime.now().isoformat()
        }
        
        return await self.send_message(message)
    
    async def send_heartbeat(self) -> bool:
        """
        Send heartbeat ping to server
        
        Returns:
            True if sent successfully
        """
        message = {
            "type": MessageType.HEARTBEAT,
            "student_id": self.student_id,
            "timestamp": datetime.now().isoformat()
        }
        
        success = await self.send_message(message)
        if success:
            self.last_heartbeat = datetime.now()
        
        return success
    
    async def heartbeat_loop(self):
        """Background task to send periodic heartbeats"""
        while self.should_run:
            if self.is_connected:
                await self.send_heartbeat()
            await asyncio.sleep(self.heartbeat_interval)
    
    async def receive_loop(self):
        """Background task to receive messages"""
        while self.should_run and self.is_connected:
            try:
                if self.websocket:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    
                    if self.on_message:
                        self.on_message(data)
                        
            except ConnectionClosed:
                print("[WS] Connection closed by server")
                self.is_connected = False
                break
            except Exception as e:
                print(f"[WS] Receive error: {e}")
                await asyncio.sleep(1)
    
    async def reconnect_loop(self):
        """Background task to handle reconnection"""
        while self.should_run:
            if not self.is_connected:
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    print(f"[WS] Attempting reconnect ({self.reconnect_attempts + 1}/{self.max_reconnect_attempts})...")
                    
                    if await self.connect():
                        print("[WS] Reconnected!")
                    else:
                        self.reconnect_attempts += 1
                        
            await asyncio.sleep(self.reconnect_delay)
    
    async def run(self):
        """
        Main run loop - connects and maintains connection
        Call this in an asyncio event loop
        """
        self.should_run = True
        
        # Initial connection
        if not await self.connect():
            print("[WS] Initial connection failed, will retry...")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self.heartbeat_loop()),
            asyncio.create_task(self.receive_loop()),
            asyncio.create_task(self.reconnect_loop()),
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            await self.disconnect()
    
    def stop(self):
        """Stop the client"""
        self.should_run = False


# ==================== SYNCHRONOUS WRAPPER ====================

class SyncWebSocketClient:
    """
    Synchronous wrapper for WebSocketClient
    Easier to use in Qt applications
    """
    
    def __init__(
        self,
        server_url: str = None,
        student_id: str = "UNKNOWN"
    ):
        self.client = WebSocketClient(server_url, student_id)
        self.loop = None
        self._thread = None
    
    def start(self):
        """Start client in background thread"""
        import threading
        
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.client.run())
        
        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop client"""
        self.client.stop()
        if self._thread:
            self._thread.join(timeout=2)
    
    def send_violation(self, behavior_label: int, confidence: float):
        """Send violation (thread-safe)"""
        if self.loop and self.client.is_connected:
            asyncio.run_coroutine_threadsafe(
                self.client.send_violation(behavior_label, confidence),
                self.loop
            )
    
    @property
    def is_connected(self) -> bool:
        return self.client.is_connected
