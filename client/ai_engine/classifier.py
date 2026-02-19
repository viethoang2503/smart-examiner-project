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
    Output: Behavior label (NORMAL, LOOKING_LEFT, LOOKING_RIGHT, HEAD_DOWN)
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
                                  3=HEAD_DOWN
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
            if h_gaze < -0.25:  # Eyes looking left
                return int(BehaviorLabel.LOOKING_LEFT)
            
            # Detect eye glancing right
            if h_gaze > 0.25:  # Eyes looking right
                return int(BehaviorLabel.LOOKING_RIGHT)
            
            # Detect eyes looking down (without head movement)
            if v_gaze < -0.3:  # Eyes looking down
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
    Detects violations with time-based filtering.
    A behavior must persist continuously for VIOLATION_DURATION_SECONDS 
    before it counts as a single violation.
    """
    
    def __init__(
        self, 
        classifier: BehaviorClassifier,
        violation_threshold: int = Config.VIOLATION_FRAME_COUNT,
        violation_duration: float = Config.VIOLATION_DURATION_SECONDS
    ):
        """
        Initialize violation detector
        
        Args:
            classifier: BehaviorClassifier instance
            violation_threshold: Number of consecutive frames for noise filtering
            violation_duration: Seconds of continuous violation to count as 1 violation
        """
        self.classifier = classifier
        self.violation_threshold = violation_threshold
        self.violation_duration = violation_duration
        
        # Frame buffer for noise filtering (short-term)
        self.frame_buffer = []
        self.max_buffer_size = violation_threshold
        
        # Time-based tracking
        self._current_violation_label = None  # Currently tracked violation behavior
        self._violation_start_time = None     # When this violation started
        self._violation_reported = False      # Whether this violation was already reported
        self._cooldown_until = None           # Cooldown after reporting
        self._COOLDOWN_SECONDS = 2.0          # Wait 2s after reporting before detecting again
    
    def detect(self, features: np.ndarray, iris_gaze: Tuple[float, float] = None) -> Tuple[bool, Optional[int], Optional[float]]:
        """
        Detect violation with time-based filtering.
        A violation is only reported when the same behavior persists 
        for >= violation_duration seconds continuously.
        
        Args:
            features: Feature vector [pitch, yaw, roll, eye_ratio, mar]
            iris_gaze: Optional tuple of (horizontal_gaze, vertical_gaze)
            
        Returns:
            Tuple of (is_violation, label, confidence)
        """
        import time
        now = time.time()
        
        # Get prediction
        label, confidence, message = self.classifier.predict_with_confidence(features, iris_gaze)
        
        # Add to frame buffer for short-term noise filtering
        self.frame_buffer.append(label)
        if len(self.frame_buffer) > self.max_buffer_size:
            self.frame_buffer.pop(0)
        
        # Not enough frames yet for noise filtering
        if len(self.frame_buffer) < self.violation_threshold:
            return False, None, None
        
        # Determine the dominant behavior in the frame buffer
        violation_labels = [l for l in self.frame_buffer if l != BehaviorLabel.NORMAL]
        
        if len(violation_labels) >= self.violation_threshold:
            # Get most common violation in buffer
            dominant_label = max(set(violation_labels), key=violation_labels.count)
            
            if violation_labels.count(dominant_label) >= self.violation_threshold:
                # We have a consistent violation behavior in recent frames
                current_behavior = dominant_label
            else:
                current_behavior = None
        else:
            # Mostly normal behavior
            current_behavior = None
        
        # Check cooldown
        if self._cooldown_until and now < self._cooldown_until:
            return False, None, None
        
        # Time-based violation tracking
        if current_behavior is not None:
            if self._current_violation_label == current_behavior:
                # Same behavior continues — check duration
                if self._violation_start_time and not self._violation_reported:
                    elapsed = now - self._violation_start_time
                    if elapsed >= self.violation_duration:
                        # VIOLATION! Behavior persisted for >= duration seconds
                        self._violation_reported = True
                        self._cooldown_until = now + self._COOLDOWN_SECONDS
                        return True, current_behavior, confidence
            else:
                # Different violation behavior started — reset timer
                self._current_violation_label = current_behavior
                self._violation_start_time = now
                self._violation_reported = False
        else:
            # Normal behavior — reset everything
            self._current_violation_label = None
            self._violation_start_time = None
            self._violation_reported = False
        
        return False, None, None
    
    def reset(self):
        """Reset all state"""
        self.frame_buffer = []
        self._current_violation_label = None
        self._violation_start_time = None
        self._violation_reported = False
        self._cooldown_until = None
    
    def get_current_state(self) -> str:
        """Get current state description"""
        if len(self.frame_buffer) == 0:
            return "No data"
        
        recent_label = self.frame_buffer[-1]
        state = VIOLATION_MESSAGES.get(recent_label, "Unknown")
        
        # Show timer info if tracking a violation
        if self._current_violation_label is not None and self._violation_start_time is not None:
            import time
            elapsed = time.time() - self._violation_start_time
            remaining = max(0, self.violation_duration - elapsed)
            if not self._violation_reported and remaining > 0:
                state += f" ({elapsed:.1f}s / {self.violation_duration}s)"
        
        return state

