"""
Shared Constants for FocusGuard AI Proctoring System
Contains behavior labels, message types, colors, and configuration defaults
"""

from enum import IntEnum
from typing import Dict

# ==================== BEHAVIOR LABELS ====================
class BehaviorLabel(IntEnum):
    """Behavior classification labels"""
    NORMAL = 0
    LOOKING_LEFT = 1
    LOOKING_RIGHT = 2
    HEAD_DOWN = 3
    TALKING = 4


# ==================== WEBSOCKET MESSAGE TYPES ====================
class MessageType:
    """WebSocket message type identifiers"""
    HEARTBEAT = "heartbeat"
    VIOLATION = "violation"
    STATUS_UPDATE = "status_update"
    CONNECT = "connect"
    DISCONNECT = "disconnect"


# ==================== STATUS COLORS ====================
class StatusColor:
    """Color codes for student status display"""
    NORMAL = "#4CAF50"      # Green - Student is behaving normally
    OFFLINE = "#9E9E9E"     # Gray - Student disconnected
    WARNING = "#FF9800"     # Orange - Minor violation
    CHEATING = "#F44336"    # Red - Active cheating detected
    
    # Aliases for compatibility
    GREEN = NORMAL
    GRAY = OFFLINE
    RED = CHEATING


# ==================== CONFIGURATION DEFAULTS ====================
class Config:
    """Default configuration values"""
    
    # Server settings
    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 8000
    
    # Client settings
    HEARTBEAT_INTERVAL = 5  # seconds
    RECONNECT_DELAY = 3     # seconds
    
    # AI Engine settings
    CAMERA_INDEX = 0
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480
    FPS_TARGET = 30
    
    # Detection thresholds (adjusted to reduce false positives)
    HEAD_YAW_THRESHOLD = 40     # degrees (left/right)
    HEAD_PITCH_THRESHOLD = 25   # degrees (down) - reduced for more sensitive head down detection
    EYE_RATIO_THRESHOLD = 0.25  # gaze detection
    MAR_THRESHOLD = 0.65        # mouth aspect ratio for talking
    
    # Noise filtering
    VIOLATION_FRAME_COUNT = 5   # consecutive frames to confirm violation
    
    # Model path
    MODEL_PATH = "ml/models/behavior_model.pkl"


# ==================== FACIAL LANDMARKS INDICES ====================
class FaceLandmarks:
    """MediaPipe Face Mesh landmark indices for key facial features"""
    
    # Nose tip (for head pose estimation)
    NOSE_TIP = 1
    
    # Chin
    CHIN = 152
    
    # Left eye corner
    LEFT_EYE_LEFT = 33
    LEFT_EYE_RIGHT = 133
    
    # Right eye corner
    RIGHT_EYE_LEFT = 362
    RIGHT_EYE_RIGHT = 263
    
    # Left eye landmarks (for gaze)
    LEFT_EYE = [33, 160, 158, 133, 153, 144]
    
    # Right eye landmarks (for gaze)
    RIGHT_EYE = [362, 385, 387, 263, 373, 380]
    
    # Mouth landmarks (for MAR calculation)
    MOUTH_TOP = 13
    MOUTH_BOTTOM = 14
    MOUTH_LEFT = 78
    MOUTH_RIGHT = 308
    
    # Iris landmarks (for eye gaze detection)
    # Left iris center is 468, right iris center is 473
    LEFT_IRIS_CENTER = 468
    RIGHT_IRIS_CENTER = 473
    
    # Eye upper/lower for vertical gaze
    LEFT_EYE_TOP = 159
    LEFT_EYE_BOTTOM = 145
    RIGHT_EYE_TOP = 386
    RIGHT_EYE_BOTTOM = 374
    
    # 3D model points for head pose (6 key points)
    POSE_POINTS_3D = [
        (0.0, 0.0, 0.0),           # Nose tip
        (0.0, -330.0, -65.0),      # Chin
        (-225.0, 170.0, -135.0),   # Left eye left corner
        (225.0, 170.0, -135.0),    # Right eye right corner
        (-150.0, -150.0, -125.0),  # Left mouth corner
        (150.0, -150.0, -125.0)    # Right mouth corner
    ]
    
    # Corresponding 2D landmark indices
    POSE_POINTS_INDICES = [1, 152, 33, 263, 61, 291]


# ==================== VIOLATION MESSAGES ====================
VIOLATION_MESSAGES: Dict[int, str] = {
    BehaviorLabel.NORMAL: "Normal",
    BehaviorLabel.LOOKING_LEFT: "Looking Left",
    BehaviorLabel.LOOKING_RIGHT: "Looking Right",
    BehaviorLabel.HEAD_DOWN: "Head Down",
    BehaviorLabel.TALKING: "Talking",
}
