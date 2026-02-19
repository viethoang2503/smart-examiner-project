#!/usr/bin/env python3
"""
FocusGuard - Real Data Collection Tool
Collects labeled face feature data from webcam for model training

Controls:
    0 - Label as NORMAL (looking at camera)
    1 - Label as LOOKING_LEFT
    2 - Label as LOOKING_RIGHT  
    3 - Label as HEAD_DOWN
    SPACE - Pause/Resume recording
    S - Save data to CSV
    Q - Quit and save
"""

import sys
import os
import cv2
import csv
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.ai_engine import FaceDetector, GeometryCalculator
from shared.constants import BehaviorLabel

# Labels mapping
LABELS = {
    ord('0'): (BehaviorLabel.NORMAL, "NORMAL"),
    ord('1'): (BehaviorLabel.LOOKING_LEFT, "LOOKING_LEFT"),
    ord('2'): (BehaviorLabel.LOOKING_RIGHT, "LOOKING_RIGHT"),
    ord('3'): (BehaviorLabel.HEAD_DOWN, "HEAD_DOWN"),
}

# Colors for labels
LABEL_COLORS = {
    BehaviorLabel.NORMAL: (0, 255, 0),      # Green
    BehaviorLabel.LOOKING_LEFT: (255, 165, 0),  # Orange
    BehaviorLabel.LOOKING_RIGHT: (255, 165, 0), # Orange
    BehaviorLabel.HEAD_DOWN: (0, 0, 255),    # Red
}


def main():
    print("=" * 70)
    print("FocusGuard - Real Data Collection Tool")
    print("=" * 70)
    print()
    print("INSTRUCTIONS:")
    print("  1. Position yourself in front of the camera")
    print("  2. Press the number key corresponding to your current behavior:")
    print("     0 = NORMAL (looking at camera)")
    print("     1 = LOOKING_LEFT")
    print("     2 = LOOKING_RIGHT")
    print("     3 = HEAD_DOWN")
    print()
    print("  SPACE = Pause/Resume recording")
    print("  S = Save data now")
    print("  Q = Quit and save")
    print()
    print("  TIP: Hold down a key to continuously record that label")
    print("=" * 70)
    print()
    
    # Initialize components
    print("Initializing...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open webcam!")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    detector = FaceDetector()
    geometry = GeometryCalculator(frame_width, frame_height)
    
    print(f"Camera: {frame_width}x{frame_height}")
    print("Ready! Start collecting data...")
    print()
    
    # Data storage
    collected_data = []
    current_label = None
    current_label_name = "NONE"
    is_recording = True
    samples_by_label = {label: 0 for label in BehaviorLabel}
    
    # Output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"ml/data/collected_data_{timestamp}.csv"
    os.makedirs("ml/data", exist_ok=True)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        
        # Mirror for natural feel
        frame = cv2.flip(frame, 1)
        display = frame.copy()
        
        # Detect face and extract features
        result = detector.detect_with_image_coords(frame)
        features = None
        
        if result is not None:
            normalized_landmarks, image_coords = result
            features, iris_gaze = geometry.extract_all_features(normalized_landmarks)
            
            # Draw face mesh outline
            for point in image_coords[::10]:  # Every 10th point
                cv2.circle(display, (int(point[0]), int(point[1])), 2, (0, 255, 255), -1)
        
        # Display status
        status_color = (0, 255, 0) if is_recording else (0, 165, 255)
        status_text = "RECORDING" if is_recording else "PAUSED"
        cv2.putText(display, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
        
        # Display current label
        if current_label is not None:
            label_color = LABEL_COLORS.get(current_label, (255, 255, 255))
            cv2.putText(display, f"Label: {current_label_name}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, label_color, 2)
        else:
            cv2.putText(display, "Label: NONE (press 0-4)", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128, 128, 128), 2)
        
        # Display sample counts
        y = 100
        cv2.putText(display, "Samples collected:", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        for label in BehaviorLabel:
            y += 25
            count = samples_by_label[label]
            color = LABEL_COLORS.get(label, (255, 255, 255))
            cv2.putText(display, f"  {label.name}: {count}", (10, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Display total
        total = sum(samples_by_label.values())
        cv2.putText(display, f"Total: {total}", (10, y + 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Display features if detected
        if features is not None:
            pitch, yaw, roll, eye_ratio, mar = features
            info_x = frame_width - 200
            cv2.putText(display, f"Pitch: {pitch:.1f}", (info_x, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(display, f"Yaw: {yaw:.1f}", (info_x, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(display, f"Roll: {roll:.1f}", (info_x, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(display, f"Eye: {eye_ratio:.2f}", (info_x, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(display, f"MAR: {mar:.2f}", (info_x, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        else:
            cv2.putText(display, "No face detected", (frame_width - 180, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Instructions at bottom
        cv2.putText(display, "Keys: 0-4=Label | SPACE=Pause | S=Save | Q=Quit", 
                   (10, frame_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        cv2.imshow("Data Collection", display)
        
        # Record data if conditions met
        if is_recording and current_label is not None and features is not None:
            collected_data.append({
                'pitch': features[0],
                'yaw': features[1],
                'roll': features[2],
                'eye_ratio': features[3],
                'mar': features[4],
                'label': current_label.value
            })
            samples_by_label[current_label] += 1
        
        # Handle key press
        key = cv2.waitKey(30) & 0xFF
        
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord(' '):
            is_recording = not is_recording
            print(f"Recording: {'ON' if is_recording else 'OFF'}")
        elif key == ord('s') or key == ord('S'):
            save_data(collected_data, output_file)
        elif key in LABELS:
            current_label, current_label_name = LABELS[key]
            print(f"Label set to: {current_label_name}")
        elif key == 255 or key == -1:
            # No key pressed - clear current label after a delay
            pass
    
    # Save on exit
    if collected_data:
        save_data(collected_data, output_file)
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    detector.release()
    
    print()
    print("=" * 70)
    print("DATA COLLECTION COMPLETE")
    print("=" * 70)
    print(f"Total samples: {sum(samples_by_label.values())}")
    for label in BehaviorLabel:
        print(f"  {label.name}: {samples_by_label[label]}")
    print(f"Data saved to: {output_file}")
    print()
    print("Next step: Run 'python ml/train_model.py --data ml/data/' to train the model")
    print("=" * 70)


def save_data(data, filepath):
    """Save collected data to CSV"""
    if not data:
        print("No data to save!")
        return
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['pitch', 'yaw', 'roll', 'eye_ratio', 'mar', 'label'])
        writer.writeheader()
        writer.writerows(data)
    
    print(f"Saved {len(data)} samples to {filepath}")


if __name__ == "__main__":
    main()
