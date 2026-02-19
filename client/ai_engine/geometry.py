"""
Geometry Calculator Module
Calculates head pose (Pitch, Yaw, Roll), eye gaze, and mouth aspect ratio
from facial landmarks for behavior detection
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from shared.constants import FaceLandmarks, Config


class GeometryCalculator:
    """
    Calculates geometric features from facial landmarks:
    - Head Pose (Pitch, Yaw, Roll) using PnP algorithm
    - Eye Gaze Ratio (left/right eye direction)
    - Mouth Aspect Ratio (for speech detection)
    """
    
    def __init__(self, frame_width: int = 640, frame_height: int = 480):
        """
        Initialize geometry calculator
        
        Args:
            frame_width: Width of video frame in pixels
            frame_height: Height of video frame in pixels
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # Camera matrix (simplified intrinsic parameters)
        focal_length = frame_width
        center = (frame_width / 2, frame_height / 2)
        
        self.camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        
        # Assuming no lens distortion
        self.dist_coeffs = np.zeros((4, 1))
        
        # 3D model points for head pose estimation (in mm)
        self.model_points_3d = np.array(FaceLandmarks.POSE_POINTS_3D, dtype=np.float64)
    
    def calculate_head_pose(
        self, 
        landmarks: List[Tuple[float, float, float]]
    ) -> Tuple[float, float, float]:
        """
        Calculate head pose angles using PnP algorithm
        
        Args:
            landmarks: List of normalized (x, y, z) facial landmarks
            
        Returns:
            Tuple of (pitch, yaw, roll) in degrees
            - Pitch: Head up/down rotation
            - Yaw: Head left/right rotation  
            - Roll: Head tilt rotation
        """
        # Extract 2D image points for key landmarks
        landmark_indices = FaceLandmarks.POSE_POINTS_INDICES
        
        image_points = []
        for idx in landmark_indices:
            if idx < len(landmarks):
                x, y, z = landmarks[idx]
                # Convert normalized coordinates to pixel coordinates
                px = int(x * self.frame_width)
                py = int(y * self.frame_height)
                image_points.append([px, py])
        
        image_points = np.array(image_points, dtype=np.float64)
        
        # Solve PnP to get rotation and translation vectors
        success, rotation_vec, translation_vec = cv2.solvePnP(
            self.model_points_3d,
            image_points,
            self.camera_matrix,
            self.dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        
        if not success:
            return 0.0, 0.0, 0.0
        
        # Convert rotation vector to rotation matrix
        rotation_mat, _ = cv2.Rodrigues(rotation_vec)
        
        # Calculate Euler angles from rotation matrix
        pitch, yaw, roll = self._rotation_matrix_to_euler_angles(rotation_mat)
        
        return pitch, yaw, roll
    
    def _rotation_matrix_to_euler_angles(self, R: np.ndarray) -> Tuple[float, float, float]:
        """
        Convert rotation matrix to Euler angles (Pitch, Yaw, Roll)
        
        Args:
            R: 3x3 rotation matrix
            
        Returns:
            Tuple of (pitch, yaw, roll) in degrees
        """
        sy = np.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
        
        singular = sy < 1e-6
        
        if not singular:
            pitch = np.arctan2(R[2, 1], R[2, 2])
            yaw = np.arctan2(-R[2, 0], sy)
            roll = np.arctan2(R[1, 0], R[0, 0])
        else:
            pitch = np.arctan2(-R[1, 2], R[1, 1])
            yaw = np.arctan2(-R[2, 0], sy)
            roll = 0
        
        # Convert to degrees
        pitch = np.degrees(pitch)
        yaw = np.degrees(yaw)
        roll = np.degrees(roll)
        
        # Normalize pitch to handle gimbal lock (when pitch is around ±180°)
        # Convert to range where 0° = looking straight, positive = looking up, negative = looking down
        if pitch > 90:
            pitch = pitch - 180
        elif pitch < -90:
            pitch = pitch + 180
        
        return pitch, yaw, roll
    
    def calculate_iris_gaze(
        self, 
        landmarks: List[Tuple[float, float, float]]
    ) -> Tuple[float, float]:
        """
        Calculate eye gaze direction based on iris position relative to eye corners
        Uses MediaPipe iris landmarks for accurate gaze tracking
        
        Args:
            landmarks: List of normalized (x, y, z) facial landmarks
            
        Returns:
            Tuple of (horizontal_gaze, vertical_gaze)
            - horizontal_gaze: -1 (looking left) to +1 (looking right), 0 = center
            - vertical_gaze: -1 (looking down) to +1 (looking up), 0 = center
        """
        # Check if we have enough landmarks (iris landmarks start at 468)
        if len(landmarks) < 478:
            return 0.0, 0.0
        
        try:
            # Left eye analysis
            left_iris = landmarks[FaceLandmarks.LEFT_IRIS_CENTER]
            left_eye_left = landmarks[FaceLandmarks.LEFT_EYE_LEFT]
            left_eye_right = landmarks[FaceLandmarks.LEFT_EYE_RIGHT]
            left_eye_top = landmarks[FaceLandmarks.LEFT_EYE_TOP]
            left_eye_bottom = landmarks[FaceLandmarks.LEFT_EYE_BOTTOM]
            
            # Right eye analysis
            right_iris = landmarks[FaceLandmarks.RIGHT_IRIS_CENTER]
            right_eye_left = landmarks[FaceLandmarks.RIGHT_EYE_LEFT]
            right_eye_right = landmarks[FaceLandmarks.RIGHT_EYE_RIGHT]
            right_eye_top = landmarks[FaceLandmarks.RIGHT_EYE_TOP]
            right_eye_bottom = landmarks[FaceLandmarks.RIGHT_EYE_BOTTOM]
            
            # Calculate horizontal gaze for left eye
            left_eye_width = left_eye_right[0] - left_eye_left[0]
            if left_eye_width > 0:
                left_iris_pos = (left_iris[0] - left_eye_left[0]) / left_eye_width
                left_h_gaze = (left_iris_pos - 0.5) * 2  # Convert to -1 to 1
            else:
                left_h_gaze = 0.0
            
            # Calculate horizontal gaze for right eye
            right_eye_width = right_eye_right[0] - right_eye_left[0]
            if right_eye_width > 0:
                right_iris_pos = (right_iris[0] - right_eye_left[0]) / right_eye_width
                right_h_gaze = (right_iris_pos - 0.5) * 2
            else:
                right_h_gaze = 0.0
            
            # Average horizontal gaze
            horizontal_gaze = (left_h_gaze + right_h_gaze) / 2
            
            # Calculate vertical gaze for left eye
            left_eye_height = left_eye_bottom[1] - left_eye_top[1]
            if left_eye_height > 0:
                left_iris_v_pos = (left_iris[1] - left_eye_top[1]) / left_eye_height
                left_v_gaze = (0.5 - left_iris_v_pos) * 2  # Inverted: up is positive
            else:
                left_v_gaze = 0.0
            
            # Calculate vertical gaze for right eye
            right_eye_height = right_eye_bottom[1] - right_eye_top[1]
            if right_eye_height > 0:
                right_iris_v_pos = (right_iris[1] - right_eye_top[1]) / right_eye_height
                right_v_gaze = (0.5 - right_iris_v_pos) * 2
            else:
                right_v_gaze = 0.0
            
            # Average vertical gaze
            vertical_gaze = (left_v_gaze + right_v_gaze) / 2
            
            return np.clip(horizontal_gaze, -1.0, 1.0), np.clip(vertical_gaze, -1.0, 1.0)
            
        except (IndexError, TypeError):
            return 0.0, 0.0

    
    def calculate_eye_gaze_ratio(
        self, 
        landmarks: List[Tuple[float, float, float]],
        eye: str = 'left'
    ) -> float:
        """
        Calculate eye gaze ratio to detect looking direction
        
        Args:
            landmarks: List of normalized (x, y, z) facial landmarks
            eye: 'left' or 'right' eye
            
        Returns:
            Gaze ratio (0.0 to 1.0)
            - Low value: looking left
            - High value: looking right
            - ~0.5: looking center
        """
        if eye == 'left':
            eye_landmarks = FaceLandmarks.LEFT_EYE
        else:
            eye_landmarks = FaceLandmarks.RIGHT_EYE
        
        # Get eye region landmarks
        eye_points = []
        for idx in eye_landmarks:
            if idx < len(landmarks):
                x, y, z = landmarks[idx]
                px = int(x * self.frame_width)
                py = int(y * self.frame_height)
                eye_points.append([px, py])
        
        if len(eye_points) < 6:
            return 0.5  # Default center value
        
        eye_points = np.array(eye_points, dtype=np.int32)
        
        # Calculate eye region bounding box
        x, y, w, h = cv2.boundingRect(eye_points)
        
        # Simple heuristic: measure horizontal position of pupil
        # This is a simplified version - ideally would use iris landmarks
        eye_center_x = x + w / 2
        eye_left = x
        eye_right = x + w
        
        # Normalize to 0-1 range
        if w > 0:
            gaze_ratio = (eye_center_x - eye_left) / w
        else:
            gaze_ratio = 0.5
        
        return np.clip(gaze_ratio, 0.0, 1.0)
    
    def calculate_mouth_aspect_ratio(
        self, 
        landmarks: List[Tuple[float, float, float]]
    ) -> float:
        """
        Calculate Mouth Aspect Ratio (MAR) to detect talking
        
        Args:
            landmarks: List of normalized (x, y, z) facial landmarks
            
        Returns:
            MAR value (higher = mouth more open)
        """
        # Get mouth landmarks
        mouth_top_idx = FaceLandmarks.MOUTH_TOP
        mouth_bottom_idx = FaceLandmarks.MOUTH_BOTTOM
        mouth_left_idx = FaceLandmarks.MOUTH_LEFT
        mouth_right_idx = FaceLandmarks.MOUTH_RIGHT
        
        if max(mouth_top_idx, mouth_bottom_idx, mouth_left_idx, mouth_right_idx) >= len(landmarks):
            return 0.0
        
        # Extract points
        top = landmarks[mouth_top_idx]
        bottom = landmarks[mouth_bottom_idx]
        left = landmarks[mouth_left_idx]
        right = landmarks[mouth_right_idx]
        
        # Calculate vertical distance (height)
        vertical_dist = self._euclidean_distance(top, bottom)
        
        # Calculate horizontal distance (width)
        horizontal_dist = self._euclidean_distance(left, right)
        
        # MAR = vertical distance / horizontal distance
        if horizontal_dist > 0:
            mar = vertical_dist / horizontal_dist
        else:
            mar = 0.0
        
        return mar
    
    def _euclidean_distance(
        self, 
        p1: Tuple[float, float, float], 
        p2: Tuple[float, float, float]
    ) -> float:
        """
        Calculate Euclidean distance between two 3D points
        
        Args:
            p1: First point (x, y, z)
            p2: Second point (x, y, z)
            
        Returns:
            Euclidean distance
        """
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2)
    
    def extract_all_features(
        self, 
        landmarks: List[Tuple[float, float, float]]
    ) -> Tuple[np.ndarray, Tuple[float, float]]:
        """
        Extract all geometric features as a feature vector
        
        Args:
            landmarks: List of normalized (x, y, z) facial landmarks
            
        Returns:
            Tuple of (features, iris_gaze)
            - features: Feature vector [pitch, yaw, roll, eye_ratio, mar]
            - iris_gaze: Tuple (horizontal_gaze, vertical_gaze) from iris tracking
        """
        # Calculate head pose
        pitch, yaw, roll = self.calculate_head_pose(landmarks)
        
        # Calculate eye gaze ratios
        left_eye_ratio = self.calculate_eye_gaze_ratio(landmarks, eye='left')
        right_eye_ratio = self.calculate_eye_gaze_ratio(landmarks, eye='right')
        
        # Average eye ratio
        avg_eye_ratio = (left_eye_ratio + right_eye_ratio) / 2.0
        
        # Calculate mouth aspect ratio
        mar = self.calculate_mouth_aspect_ratio(landmarks)
        
        # Calculate iris gaze
        iris_h_gaze, iris_v_gaze = self.calculate_iris_gaze(landmarks)
        
        # Create feature vector (keep same format for model compatibility)
        features = np.array([pitch, yaw, roll, avg_eye_ratio, mar], dtype=np.float32)
        
        return features, (iris_h_gaze, iris_v_gaze)
    
    def detect_behavior(
        self, 
        features: np.ndarray, 
        thresholds: Optional[dict] = None
    ) -> str:
        """
        Simple rule-based behavior detection from features
        
        Args:
            features: Feature vector [pitch, yaw, roll, eye_ratio, mar]
            thresholds: Optional custom thresholds
            
        Returns:
            Behavior label: 'NORMAL', 'LOOKING_LEFT', 'LOOKING_RIGHT', 'HEAD_DOWN'
        """
        if thresholds is None:
            thresholds = {
                'yaw_left': -Config.HEAD_YAW_THRESHOLD,
                'yaw_right': Config.HEAD_YAW_THRESHOLD,
                'pitch_down': -Config.HEAD_PITCH_THRESHOLD,
            }
        
        pitch, yaw, roll, eye_ratio, mar = features
        
        # Check for head down (pitch is NEGATIVE when looking down)
        if pitch < thresholds['pitch_down']:
            return 'HEAD_DOWN'
        
        # Check for looking left
        if yaw < thresholds['yaw_left']:
            return 'LOOKING_LEFT'
        
        # Check for looking right
        if yaw > thresholds['yaw_right']:
            return 'LOOKING_RIGHT'
        
        return 'NORMAL'
