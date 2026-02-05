"""
AI Engine Module for FocusGuard
Contains face detection, geometry calculations, and behavior classification
"""

from .face_detector import FaceDetector, calculate_distance, calculate_angle
from .geometry import GeometryCalculator
from .classifier import BehaviorClassifier, ViolationDetector
from .screenshot import ScreenshotCapture

__all__ = [
    'FaceDetector',
    'GeometryCalculator',
    'BehaviorClassifier',
    'ViolationDetector',
    'ScreenshotCapture',
    'calculate_distance',
    'calculate_angle',
]
