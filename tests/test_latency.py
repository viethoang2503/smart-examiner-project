"""
FocusGuard Latency Tests
Tests performance of AI pipeline and API responses
"""

import time
import sys
import os
import cv2
import numpy as np

# Add project path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.ai_engine import FaceDetector, GeometryCalculator, BehaviorClassifier


def measure_ai_pipeline_latency():
    """
    Test the complete AI pipeline latency
    Requirement: < 100ms per frame
    """
    print("=" * 60)
    print("FocusGuard AI Pipeline Latency Test")
    print("=" * 60)
    
    # Initialize components
    print("\n⏳ Loading AI components...")
    
    start = time.time()
    detector = FaceDetector()
    detector_load_time = time.time() - start
    print(f"  Face Detector loaded: {detector_load_time*1000:.1f}ms")
    
    start = time.time()
    geometry = GeometryCalculator(640, 480)
    geometry_load_time = time.time() - start
    print(f"  Geometry Calculator loaded: {geometry_load_time*1000:.1f}ms")
    
    start = time.time()
    classifier = BehaviorClassifier()
    classifier_load_time = time.time() - start
    print(f"  Behavior Classifier loaded: {classifier_load_time*1000:.1f}ms")
    
    # Open webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open webcam for latency test")
        return None
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("\n⏳ Running latency tests (50 frames)...")
    
    # Collect timing data
    timings = {
        "capture": [],
        "detection": [],
        "geometry": [],
        "classification": [],
        "total": []
    }
    
    num_frames = 50
    successful_frames = 0
    
    for i in range(num_frames):
        total_start = time.time()
        
        # Frame capture
        capture_start = time.time()
        ret, frame = cap.read()
        timings["capture"].append((time.time() - capture_start) * 1000)
        
        if not ret:
            continue
        
        # Face detection
        detect_start = time.time()
        result = detector.detect_with_image_coords(frame)
        timings["detection"].append((time.time() - detect_start) * 1000)
        
        if result is not None:
            normalized_landmarks, _ = result
            successful_frames += 1
            
            # Geometry calculation
            geo_start = time.time()
            features, iris_gaze = geometry.extract_all_features(normalized_landmarks)
            timings["geometry"].append((time.time() - geo_start) * 1000)
            
            # Classification
            class_start = time.time()
            label = classifier.predict(features, iris_gaze)
            timings["classification"].append((time.time() - class_start) * 1000)
        
        timings["total"].append((time.time() - total_start) * 1000)
    
    cap.release()
    detector.release()
    
    # Calculate statistics
    print("\n" + "=" * 60)
    print("LATENCY RESULTS")
    print("=" * 60)
    
    results = {}
    
    for stage, times in timings.items():
        if times:
            avg = np.mean(times)
            min_t = np.min(times)
            max_t = np.max(times)
            std = np.std(times)
            
            results[stage] = {
                "avg": avg,
                "min": min_t,
                "max": max_t,
                "std": std
            }
            
            status = "✅" if avg < 100 else "⚠️"
            print(f"{status} {stage.capitalize():15} Avg: {avg:6.2f}ms | Min: {min_t:6.2f}ms | Max: {max_t:6.2f}ms")
    
    # Overall assessment
    total_avg = results.get("total", {}).get("avg", 0)
    print("\n" + "-" * 60)
    
    if total_avg < 100:
        print(f"✅ PASS: Average total latency {total_avg:.2f}ms < 100ms requirement")
    else:
        print(f"❌ FAIL: Average total latency {total_avg:.2f}ms > 100ms requirement")
    
    print(f"\nFrames processed: {num_frames}")
    print(f"Faces detected: {successful_frames} ({successful_frames/num_frames*100:.1f}%)")
    print(f"FPS equivalent: {1000/total_avg:.1f} fps")
    
    return results


def measure_api_latency():
    """Test API response latency"""
    import requests
    from shared.constants import Config
    
    BASE_URL = f"http://localhost:{Config.SERVER_PORT}"
    
    print("\n" + "=" * 60)
    print("API Latency Test")
    print("=" * 60)
    
    try:
        timings = []
        
        for i in range(20):
            start = time.time()
            response = requests.get(f"{BASE_URL}/", timeout=5)
            elapsed = (time.time() - start) * 1000
            timings.append(elapsed)
        
        avg = np.mean(timings)
        min_t = np.min(timings)
        max_t = np.max(timings)
        
        status = "✅" if avg < 50 else "⚠️"
        print(f"{status} API Response: Avg: {avg:.2f}ms | Min: {min_t:.2f}ms | Max: {max_t:.2f}ms")
        
        return {"avg": avg, "min": min_t, "max": max_t}
        
    except requests.exceptions.ConnectionError:
        print("❌ Server not running")
        return None


def generate_report(ai_results, api_results):
    """Generate latency test report"""
    print("\n" + "=" * 60)
    print("LATENCY TEST REPORT")
    print("=" * 60)
    
    report = []
    report.append("# FocusGuard Latency Test Report\n")
    report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if ai_results:
        report.append("\n## AI Pipeline Latency\n")
        for stage, data in ai_results.items():
            report.append(f"- **{stage.capitalize()}**: {data['avg']:.2f}ms (avg)\n")
    
    if api_results:
        report.append("\n## API Latency\n")
        report.append(f"- **Response Time**: {api_results['avg']:.2f}ms (avg)\n")
    
    # Save report
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tests",
        "latency_report.md"
    )
    
    with open(report_path, "w") as f:
        f.writelines(report)
    
    print(f"\n📄 Report saved to: {report_path}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("FocusGuard Performance Testing")
    print("=" * 60)
    
    ai_results = measure_ai_pipeline_latency()
    api_results = measure_api_latency()
    
    if ai_results or api_results:
        generate_report(ai_results, api_results)
    
    print("\n✅ Latency tests completed!")
