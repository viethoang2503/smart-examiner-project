"""
FocusGuard Screenshot Capture Module
Captures webcam frames as evidence when violations are detected
"""

import os
import cv2
import base64
from datetime import datetime
from typing import Optional, Tuple
import numpy as np


class ScreenshotCapture:
    """
    Captures and encodes webcam frames for violation evidence
    """
    
    def __init__(self, save_dir: str = None):
        """
        Initialize screenshot capture
        
        Args:
            save_dir: Directory to save local copies (optional)
        """
        self.save_dir = save_dir
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir)
    
    def capture_frame(
        self, 
        frame: np.ndarray,
        student_id: str,
        exam_code: str,
        behavior_name: str,
        save_local: bool = True
    ) -> Tuple[str, str, Optional[str]]:
        """
        Capture a frame as violation evidence
        
        Args:
            frame: OpenCV frame (BGR numpy array)
            student_id: Student identifier
            exam_code: Exam code
            behavior_name: Type of violation
            save_local: Whether to save a local copy
            
        Returns:
            Tuple of (timestamp, base64_image, local_path or None)
        """
        timestamp = datetime.now().isoformat()
        
        # Add overlay with violation info
        annotated = self._annotate_frame(frame, behavior_name, timestamp)
        
        # Encode to JPEG
        success, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            raise RuntimeError("Failed to encode frame")
        
        # Convert to base64
        base64_image = base64.b64encode(buffer).decode('utf-8')
        
        # Save local copy if requested
        local_path = None
        if save_local and self.save_dir:
            filename = f"{exam_code}_{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{behavior_name}.jpg"
            local_path = os.path.join(self.save_dir, filename)
            cv2.imwrite(local_path, annotated)
        
        return timestamp, base64_image, local_path
    
    def _annotate_frame(
        self, 
        frame: np.ndarray, 
        behavior_name: str, 
        timestamp: str
    ) -> np.ndarray:
        """Add violation info overlay to frame"""
        annotated = frame.copy()
        height, width = annotated.shape[:2]
        
        # Add semi-transparent header bar
        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, 0), (width, 50), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, annotated, 0.3, 0, annotated)
        
        # Add violation text
        cv2.putText(
            annotated, 
            f"VIOLATION: {behavior_name}", 
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.7, 
            (0, 0, 255), 
            2
        )
        
        # Add timestamp
        time_str = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            annotated, 
            time_str, 
            (width - 200, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            (255, 255, 255), 
            1
        )
        
        # Add red border
        cv2.rectangle(annotated, (0, 0), (width-1, height-1), (0, 0, 255), 3)
        
        return annotated
    
    @staticmethod
    def decode_base64_image(base64_str: str) -> np.ndarray:
        """Decode base64 string back to OpenCV frame"""
        img_data = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return frame
    
    @staticmethod
    def save_base64_to_file(base64_str: str, filepath: str) -> bool:
        """Save base64 image to file"""
        try:
            img_data = base64.b64decode(base64_str)
            with open(filepath, 'wb') as f:
                f.write(img_data)
            return True
        except Exception as e:
            print(f"Error saving image: {e}")
            return False


if __name__ == "__main__":
    # Test the screenshot capture
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        capture = ScreenshotCapture(save_dir="./test_screenshots")
        timestamp, b64, path = capture.capture_frame(
            frame, 
            "TEST_001", 
            "ABC123",
            "LOOKING_AWAY"
        )
        print(f"Captured at: {timestamp}")
        print(f"Base64 length: {len(b64)}")
        print(f"Saved to: {path}")
    else:
        print("Failed to capture from webcam")
