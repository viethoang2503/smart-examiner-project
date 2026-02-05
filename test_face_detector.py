"""
Test script for Face Detector module
Press 'q' to quit
"""

import cv2
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.ai_engine.face_detector import FaceDetector


def main():
    print("=" * 60)
    print("FocusGuard - Face Detector Test")
    print("=" * 60)
    print("Initializing webcam...")
    
    # Open webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ ERROR: Cannot open webcam!")
        print("Please check if your camera is connected and not being used by another app.")
        return
    
    # Set camera resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("✅ Webcam opened successfully!")
    print("Initializing MediaPipe Face Mesh...")
    
    # Initialize face detector
    detector = FaceDetector(
        max_num_faces=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    print("✅ Face Detector initialized!")
    print("\n" + "=" * 60)
    print("INSTRUCTIONS:")
    print("  - Look at the camera")
    print("  - Green dots will appear on your face landmarks")
    print("  - Press 'q' to quit")
    print("=" * 60 + "\n")
    
    frame_count = 0
    detection_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to grab frame")
                break
            
            frame_count += 1
            
            # Detect face landmarks
            result = detector.detect_with_image_coords(frame)
            
            if result is not None:
                normalized_landmarks, pixel_landmarks = result
                detection_count += 1
                
                # Draw landmarks
                for px, py in pixel_landmarks:
                    cv2.circle(frame, (px, py), 1, (0, 255, 0), -1)
                
                # Display info
                info_text = f"Face Detected | Landmarks: {len(pixel_landmarks)}"
                cv2.putText(frame, info_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Display detection rate
                detection_rate = (detection_count / frame_count) * 100
                rate_text = f"Detection Rate: {detection_rate:.1f}%"
                cv2.putText(frame, rate_text, (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            else:
                # No face detected
                cv2.putText(frame, "No Face Detected", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Display FPS
            fps_text = f"Frame: {frame_count}"
            cv2.putText(frame, fps_text, (10, frame.shape[0] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Show frame
            cv2.imshow('FocusGuard - Face Detector Test', frame)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n👋 Quitting...")
                break
                
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    
    finally:
        # Cleanup
        print("\n" + "=" * 60)
        print("STATISTICS:")
        print(f"  Total Frames: {frame_count}")
        print(f"  Faces Detected: {detection_count}")
        if frame_count > 0:
            print(f"  Detection Rate: {(detection_count/frame_count)*100:.1f}%")
        print("=" * 60)
        
        cap.release()
        cv2.destroyAllWindows()
        detector.release()
        print("✅ Resources released. Goodbye!")


if __name__ == "__main__":
    main()
