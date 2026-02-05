"""
Behavior Classifier Module
Uses trained Random Forest model to classify student behavior
from facial feature vectors
"""

import numpy as np
import joblib
import os
import sys
from typing import Optional, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from shared.constants import BehaviorLabel, Config, VIOLATION_MESSAGES


class BehaviorClassifier:
    """
    Classifies student behavior using a trained Random Forest model
    Input: Feature vector [pitch, yaw, roll, eye_ratio, mar]
    Output: Behavior label (NORMAL, LOOKING_LEFT, LOOKING_RIGHT, HEAD_DOWN, TALKING)
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize behavior classifier
        
        Args:
            model_path: Path to trained model file (.pkl)
        """
        if model_path is None:
            # Use default model path
            model_path = os.path.join(
                os.path.dirname(__file__), 
                '../../' + Config.MODEL_PATH
            )
        
        self.model_path = model_path
        self.model = None
        self.load_model()
    
    def load_model(self):
        """Load trained Random Forest model from file"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Model file not found: {self.model_path}\n"
                f"Please train the model first by running: python ml/train_model.py"
            )
        
        try:
            self.model = joblib.load(self.model_path)
            print(f"✅ Model loaded from: {self.model_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")
    
    def predict(self, features: np.ndarray, iris_gaze: Tuple[float, float] = None) -> int:
        """
        Predict behavior label from feature vector
        
        Args:
            features: Feature vector [pitch, yaw, roll, eye_ratio, mar]
            iris_gaze: Optional tuple of (horizontal_gaze, vertical_gaze) from iris tracking
            
        Returns:
            Behavior label (int): 0=NORMAL, 1=LOOKING_LEFT, 2=LOOKING_RIGHT, 
                                  3=HEAD_DOWN, 4=TALKING
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        # Ensure features is 2D array (1 sample, 5 features)
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # Rule-based override for HEAD_DOWN (more sensitive than model)
        # pitch > 20 degrees = head tilted down
        pitch = features[0][0]  # First feature is pitch
        if pitch > 20:  # Sensitive threshold for head down
            return int(BehaviorLabel.HEAD_DOWN)
        
        # Eye gaze detection (if iris_gaze provided)
        if iris_gaze is not None:
            h_gaze, v_gaze = iris_gaze
            
            # Detect eye glancing left (looking left with eyes, not head)
            if h_gaze < -0.35:  # Eyes looking left
                return int(BehaviorLabel.LOOKING_LEFT)
            
            # Detect eye glancing right
            if h_gaze > 0.35:  # Eyes looking right
                return int(BehaviorLabel.LOOKING_RIGHT)
            
            # Detect eyes looking down (without head movement)
            if v_gaze < -0.4:  # Eyes looking down
                return int(BehaviorLabel.HEAD_DOWN)
        
        # Predict using ML model
        prediction = self.model.predict(features)[0]
        
        return int(prediction)

    
    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """
        Get prediction probabilities for all classes
        
        Args:
            features: Feature vector [pitch, yaw, roll, eye_ratio, mar]
            
        Returns:
            Array of probabilities for each class
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        # Ensure features is 2D array
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # Get probabilities
        probabilities = self.model.predict_proba(features)[0]
        
        return probabilities
    
    def predict_with_confidence(
        self, 
        features: np.ndarray,
        iris_gaze: Tuple[float, float] = None
    ) -> Tuple[int, float, str]:
        """
        Predict behavior with confidence score and message
        
        Args:
            features: Feature vector [pitch, yaw, roll, eye_ratio, mar]
            iris_gaze: Optional tuple of (horizontal_gaze, vertical_gaze)
            
        Returns:
            Tuple of (label, confidence, message)
            - label: Behavior label (int)
            - confidence: Prediction confidence (0.0 to 1.0)
            - message: Human-readable behavior description
        """
        # Get prediction and probabilities
        label = self.predict(features, iris_gaze)
        probabilities = self.predict_proba(features)
        confidence = probabilities[label] if label < len(probabilities) else 0.9
        
        # Get message
        message = VIOLATION_MESSAGES.get(label, "Unknown")
        
        return label, confidence, message


class ViolationDetector:
    """
    Detects violations with noise filtering
    Uses consecutive frame counting to avoid false positives
    """
    
    def __init__(
        self, 
        classifier: BehaviorClassifier,
        violation_threshold: int = Config.VIOLATION_FRAME_COUNT
    ):
        """
        Initialize violation detector
        
        Args:
            classifier: BehaviorClassifier instance
            violation_threshold: Number of consecutive frames to confirm violation
        """
        self.classifier = classifier
        self.violation_threshold = violation_threshold
        
        # Frame buffer for noise filtering
        self.frame_buffer = []
        self.max_buffer_size = violation_threshold
    
    def detect(self, features: np.ndarray, iris_gaze: Tuple[float, float] = None) -> Tuple[bool, Optional[int], Optional[float]]:
        """
        Detect violation with noise filtering
        
        Args:
            features: Feature vector [pitch, yaw, roll, eye_ratio, mar]
            iris_gaze: Optional tuple of (horizontal_gaze, vertical_gaze) for eye tracking
            
        Returns:
            Tuple of (is_violation, label, confidence)
            - is_violation: True if violation detected after filtering
            - label: Behavior label (None if no violation)
            - confidence: Prediction confidence (None if no violation)
        """
        # Get prediction
        label, confidence, message = self.classifier.predict_with_confidence(features, iris_gaze)
        
        # Add to buffer
        self.frame_buffer.append(label)
        
        # Keep buffer size limited
        if len(self.frame_buffer) > self.max_buffer_size:
            self.frame_buffer.pop(0)
        
        # Check if we have enough frames
        if len(self.frame_buffer) < self.violation_threshold:
            return False, None, None
        
        # Count occurrences of each label in buffer
        violation_labels = [l for l in self.frame_buffer if l != BehaviorLabel.NORMAL]
        
        # If all recent frames show the same violation, confirm it
        if len(violation_labels) >= self.violation_threshold:
            # Get most common violation
            most_common = max(set(violation_labels), key=violation_labels.count)
            
            # Check if it appears enough times
            if violation_labels.count(most_common) >= self.violation_threshold:
                return True, most_common, confidence
        
        return False, None, None
    
    def reset(self):
        """Reset frame buffer"""
        self.frame_buffer = []
    
    def get_current_state(self) -> str:
        """
        Get current state description
        
        Returns:
            Human-readable state description
        """
        if len(self.frame_buffer) == 0:
            return "No data"
        
        recent_label = self.frame_buffer[-1]
        return VIOLATION_MESSAGES.get(recent_label, "Unknown")
