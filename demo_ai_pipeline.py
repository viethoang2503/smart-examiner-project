"""
Complete AI Pipeline Demo
Tests Face Detection -> Geometry Calculation -> Behavior Classification
Press 'q' to quit
"""

import cv2
import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.ai_engine import FaceDetector, GeometryCalculator, BehaviorClassifier, ViolationDetector
from shared.constants import VIOLATION_MESSAGES


def main():
    print("=" * 70)
    print("FocusGuard - Complete AI Pipeline Demo")
    print("=" * 70)
    print("\nInitializing components...")
    
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ ERROR: Cannot open webcam!")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"✅ Webcam: {frame_width}x{frame_height}")
    
    # Initialize AI components
    print("⏳ Loading AI components...")
    
    try:
        detector = FaceDetector()
        print("  ✅ Face Detector")
        
        geometry = GeometryCalculator(frame_width, frame_height)
        print("  ✅ Geometry Calculator")
        
        classifier = BehaviorClassifier()
        print("  ✅ Behavior Classifier")
        
        violation_detector = ViolationDetector(classifier, violation_threshold=5)
        print("  ✅ Violation Detector")
        
    except Exception as e:
        print(f"❌ Error initializing AI: {e}")
        cap.release()
        return
    
    print("\n" + "=" * 70)
    print("INSTRUCTIONS:")
    print("  - Look at the camera to see your behavior being analyzed")
    print("  - Try looking left/right, looking down, or talking")
    print("  - Press 'q' to quit")
    print("=" * 70 + "\n")
    
    frame_count = 0
    detection_count = 0
    violation_count = 0
    
    # Colors
    COLOR_GREEN = (0, 255, 0)
    COLOR_RED = (0, 0, 255)
    COLOR_YELLOW = (0, 255, 255)
    COLOR_WHITE = (255, 255, 255)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Detect face landmarks
            result = detector.detect_with_image_coords(frame)
            
            if result is not None:
                normalized_landmarks, pixel_landmarks = result
                detection_count += 1
                
                # Draw landmarks (smaller circles for cleaner look)
                for px, py in pixel_landmarks[::5]:  # Draw every 5th landmark
                    cv2.circle(frame, (px, py), 1, COLOR_GREEN, -1)
                
                # Calculate geometry features
                features, iris_gaze = geometry.extract_all_features(normalized_landmarks)
                pitch, yaw, roll, eye_ratio, mar = features
                h_gaze, v_gaze = iris_gaze
                
                # Classify behavior (with iris gaze)
                is_violation, label, confidence = violation_detector.detect(features, iris_gaze)
                
                # Determine color and status
                if is_violation:
                    status_color = COLOR_RED
                    status_text = "[!] VIOLATION"
                    behavior = VIOLATION_MESSAGES.get(label, "Unknown")
                    violation_count += 1
                else:
                    status_color = COLOR_GREEN
                    status_text = "[OK] NORMAL"
                    current_state = violation_detector.get_current_state()
                    behavior = current_state
                
                # Display info panel
                y_offset = 30
                line_height = 30
                
                # Status
                cv2.putText(frame, status_text, (10, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                
                # Behavior
                y_offset += line_height
                cv2.putText(frame, f"Behavior: {behavior}", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_WHITE, 2)
                
                # Head Pose
                y_offset += line_height
                cv2.putText(frame, f"Pitch: {pitch:+.1f}  Yaw: {yaw:+.1f}  Roll: {roll:+.1f}", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_YELLOW, 1)
                
                # Eye & Mouth
                y_offset += line_height
                cv2.putText(frame, f"Eye: {eye_ratio:.2f}  MAR: {mar:.2f}", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_YELLOW, 1)
                
                # Eye Gaze (iris tracking)
                y_offset += line_height
                gaze_color = COLOR_RED if abs(h_gaze) > 0.35 or v_gaze < -0.4 else COLOR_GREEN
                cv2.putText(frame, f"Eye Gaze - H: {h_gaze:+.2f}  V: {v_gaze:+.2f}", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, gaze_color, 1)
                
                # Statistics at bottom
                stats_y = frame.shape[0] - 40
                cv2.putText(frame, f"Frame: {frame_count} | Detection Rate: {(detection_count/frame_count)*100:.1f}%", 
                           (10, stats_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_WHITE, 1)
                
                stats_y += 20
                cv2.putText(frame, f"Violations: {violation_count}", 
                           (10, stats_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_RED, 1)
                
            else:
                # No face detected
                cv2.putText(frame, "No Face Detected", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_RED, 2)
            
            # Show frame
            cv2.imshow('FocusGuard - AI Pipeline Demo', frame)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n👋 Quitting...")
                break
                
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    
    finally:
        # Cleanup and print statistics
        print("\n" + "=" * 70)
        print("SESSION STATISTICS:")
        print("=" * 70)
        print(f"  Total Frames: {frame_count}")
        print(f"  Faces Detected: {detection_count}")
        if frame_count > 0:
            print(f"  Detection Rate: {(detection_count/frame_count)*100:.1f}%")
        print(f"  Violations Detected: {violation_count}")
        print("=" * 70)
         
        cap.release()
        cv2.destroyAllWindows()
        detector.release()
        print("\n✅ Resources released. Goodbye!")


if __name__ == "__main__":
    main()
