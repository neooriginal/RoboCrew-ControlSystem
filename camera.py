"""
RoboCrew Control System - Camera Module
Handles camera initialization and MJPEG streaming.
"""

import time
import cv2

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
    while state.running and state.camera and state.camera.isOpened():
        try:
            # Grab and retrieve to clear buffer
            ret, frame = state.camera.read()
            if ret:
                state.latest_frame = frame
            else:
                time.sleep(0.01)
        except Exception:
            time.sleep(0.1)


def generate_frames():
    """MJPEG video stream generator using the latest captured frame."""
    while state.running:
        if not hasattr(state, 'latest_frame') or state.latest_frame is None:
            time.sleep(0.05)
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
            state.last_error = f"Camera error: {str(e)}"
            time.sleep(0.05)


def release_camera():
    """Release camera resources."""
    if state.camera:
        try:
            state.camera.release()
            print("✓ Camera released")
        except Exception as e:
            print(f"✗ Camera cleanup error: {e}")
    state.camera = None
