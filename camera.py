"""
RoboCrew Control System - Camera Module
Handles camera initialization and MJPEG streaming.
"""

import time
import cv2
import numpy as np

from config import CAMERA_PORT, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_BUFFER_SIZE, JPEG_QUALITY
from state import state


import threading

def init_camera():
    """Initialize the camera and start background capture thread."""
    print(f"📷 Connecting camera ({CAMERA_PORT})...", end=" ", flush=True)
    try:
        # Check if already initialized
        if state.camera is not None and state.camera.isOpened():
            print("✓ (Already open)")
            return True

        camera = cv2.VideoCapture(CAMERA_PORT)
        # We still set these, though the thread handles the rate
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Minimal internal buffer
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        
        if camera.isOpened():
            print("✓")
            state.camera = camera
            
            # Start background capture thread
            capture_thread = threading.Thread(target=_capture_loop, daemon=True)
            capture_thread.start()
            
            return True
        else:
            print("⚠ Warning: Camera may not be available")
            state.last_error = "Camera not available"
            state.camera = None
            return False
    except Exception as e:
        print(f"✗ Failed: {e}")
        state.camera = None
        state.last_error = f"Camera init failed: {e}"
        return False


def _capture_loop():
    """Background thread to constantly read the latest frame."""
    print("[Camera] Capture thread started")
    frames_read = 0
    while state.running and state.camera and state.camera.isOpened():
        try:
            # Grab and retrieve to clear buffer
            ret, frame = state.camera.read()
            if ret:
                state.latest_frame = frame
                frames_read += 1
                if frames_read % 100 == 0:
                    print(f"[Camera] Captured {frames_read} frames", end='\r')
            else:
                print("[Camera] Failed to read frame")
                time.sleep(0.01)
        except Exception as e:
            print(f"[Camera] Thread error: {e}")
            time.sleep(0.1)
    print("[Camera] Capture thread stopped")


def generate_frames():
    """MJPEG video stream generator using the latest captured frame."""
    
    # Create a placeholder frame (black image with text)
    blank_frame = np.zeros((180, 320, 3), np.uint8)
    cv2.putText(blank_frame, "WAITING FOR CAMERA...", (20, 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    _, blank_buffer = cv2.imencode('.jpg', blank_frame, [cv2.IMWRITE_JPEG_QUALITY, 20])
    blank_bytes = blank_buffer.tobytes()

    while state.running:
        if not hasattr(state, 'latest_frame') or state.latest_frame is None:
            # Yield placeholder instead of blocking
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + blank_bytes + b'\r\n')
            time.sleep(0.5)
            continue
        
        try:
            # Get the strict latest frame (copy to avoid threading issues during resize)
            frame = state.latest_frame
            
            # Resize BEFORE encoding (Aggressive 320x180 for max FPS)
            # Use INTER_NEAREST for speed. AI still gets full 720p frame.
            stream_frame = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_NEAREST)

            # Ultra-low quality for speed (Q=20)
            # Use extremely fast encoding
            _, buffer = cv2.imencode('.jpg', stream_frame, [
                cv2.IMWRITE_JPEG_QUALITY, 20,
                cv2.IMWRITE_JPEG_OPTIMIZE, 0
            ])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            # Limit send rate slightly to avoid overwhelming slow clients
            # matching the VR client's 30fps request
            time.sleep(0.03)
            
        except Exception as e:
            print(f"[Stream] Error: {e}")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + blank_bytes + b'\r\n')
            time.sleep(0.1)


def release_camera():
    """Release camera resources."""
    if state.camera:
        try:
            state.camera.release()
            print("✓ Camera released")
        except Exception as e:
            print(f"✗ Camera cleanup error: {e}")
    state.camera = None
