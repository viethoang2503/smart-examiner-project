"""
Face Detector Module using MediaPipe Face Landmarker
Extracts 468 facial landmarks from webcam frames at 30+ FPS
Compatible with MediaPipe 0.10.32+
"""

import cv2
import mediapipe as mp
import numpy as np
import os
import urllib.request
from typing import Optional, Tuple, List


class FaceDetector:
    """
    Detects faces and extracts facial landmarks using MediaPipe Face Landmarker
    Optimized for real-time performance on CPU
    """
    
    def __init__(
        self,
        max_num_faces: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        model_path: Optional[str] = None
    ):
        """
        Initialize MediaPipe Face Landmarker (MediaPipe 0.10+)
        
        Args:
            max_num_faces: Maximum number of faces to detect
            min_detection_confidence: Minimum confidence for face detection
            min_tracking_confidence: Minimum confidence for landmark tracking
            model_path: Path to face_landmarker.task model file (auto-downloaded if not provided)
        """
        # Download model if not exists
        if model_path is None:
            model_path = self._download_model()
        
        # Create FaceLandmarker using new MediaPipe 0.10+ API
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,  # Use VIDEO mode for webcam
            num_faces=max_num_faces,
            min_face_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False
        )
        
        self.detector = vision.FaceLandmarker.create_from_options(options)
        self.frame_timestamp_ms = 0
    
    def _download_model(self) -> str:
        """
        Download face landmarker model if not exists
        
        Returns:
            Path to model file
        """
        model_dir = os.path.join(os.path.dirname(__file__), '../../ml/models')
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, 'face_landmarker.task')
        
        if not os.path.exists(model_path):
            print("⏳ Downloading face landmarker model...")
            model_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            
            try:
                urllib.request.urlretrieve(model_url, model_path)
                print(f"✅ Model downloaded to: {model_path}")
            except Exception as e:
                raise RuntimeError(f"Failed to download model: {e}")
        
        return model_path
        
    def detect(self, frame: np.ndarray) -> Optional[List[Tuple[float, float, float]]]:
        """
        Detect face and extract landmarks from a single frame
        
        Args:
            frame: BGR image from OpenCV (numpy array)
            
        Returns:
            List of (x, y, z) tuples for each landmark, or None if no face detected
            Coordinates are normalized (0.0 to 1.0)
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to MediaPipe Image format
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Increment timestamp for video mode
        self.frame_timestamp_ms += 33  # ~30 FPS
        
        # Detect landmarks
        detection_result = self.detector.detect_for_video(mp_image, self.frame_timestamp_ms)
        
        # Check if any face was detected
        if not detection_result.face_landmarks:
            return None
        
        # Extract landmarks from the first detected face
        face_landmarks = detection_result.face_landmarks[0]
        
        # Convert to list of tuples
        landmarks = []
        for landmark in face_landmarks:
            landmarks.append((landmark.x, landmark.y, landmark.z))
        
        return landmarks
    
    def detect_with_image_coords(
        self, 
        frame: np.ndarray
    ) -> Optional[Tuple[List[Tuple[float, float, float]], List[Tuple[int, int]]]]:
        """
        Detect face and return both normalized and pixel coordinates
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            Tuple of (normalized_landmarks, pixel_landmarks) or None if no face detected
            - normalized_landmarks: List of (x, y, z) in range [0, 1]
            - pixel_landmarks: List of (x, y) in pixel coordinates
        """
        h, w = frame.shape[:2]
        
        # Get normalized landmarks
        normalized_landmarks = self.detect(frame)
        if normalized_landmarks is None:
            return None
        
        # Convert to pixel coordinates
        pixel_landmarks = []
        for x, y, z in normalized_landmarks:
            px = int(x * w)
            py = int(y * h)
            pixel_landmarks.append((px, py))
        
        return normalized_landmarks, pixel_landmarks
    
    def draw_landmarks(
        self, 
        frame: np.ndarray, 
        landmarks: List[Tuple[float, float, float]],
        draw_connections: bool = True
    ) -> np.ndarray:
        """
        Draw facial landmarks on the frame for visualization
        
        Args:
            frame: BGR image to draw on
            landmarks: List of normalized (x, y, z) landmarks
            draw_connections: Whether to draw mesh connections
            
        Returns:
            Frame with landmarks drawn
        """
        h, w = frame.shape[:2]
        
        # Draw landmarks as circles
        for x, y, z in landmarks:
            px = int(x * w)
            py = int(y * h)
            cv2.circle(frame, (px, py), 1, (0, 255, 0), -1)
        
        return frame
    
    def get_specific_landmarks(
        self,
        landmarks: List[Tuple[float, float, float]],
        indices: List[int]
    ) -> List[Tuple[float, float, float]]:
        """
        Extract specific landmarks by their indices
        
        Args:
            landmarks: Full list of 468 landmarks
            indices: List of landmark indices to extract
            
        Returns:
            List of selected landmarks
        """
        return [landmarks[i] for i in indices if i < len(landmarks)]
    
    def release(self):
        """Release MediaPipe resources"""
        self.detector.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        self.release()


# ==================== UTILITY FUNCTIONS ====================

def calculate_distance(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    """
    Calculate Euclidean distance between two 3D points
    
    Args:
        p1: First point (x, y, z)
        p2: Second point (x, y, z)
        
    Returns:
        Euclidean distance
    """
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2)


def calculate_angle(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
    """
    Calculate angle formed by three 2D points (p1-p2-p3)
    
    Args:
        p1, p2, p3: Points in (x, y) format
        
    Returns:
        Angle in degrees
    """
    v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
    v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
    
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
    angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
    
    return np.degrees(angle)
