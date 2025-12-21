"""
RoboCrew Control System - Camera Module
Handles camera initialization and MJPEG streaming.
"""

import time
import cv2

from config import CAMERA_PORT, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_BUFFER_SIZE, JPEG_QUALITY
from state import state


def init_camera():
    """Initialize the camera with optimal settings for low latency."""
    print(f"📷 Connecting camera ({CAMERA_PORT})...", end=" ", flush=True)
    try:
        camera = cv2.VideoCapture(CAMERA_PORT)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, CAMERA_BUFFER_SIZE)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        
        if camera.isOpened():
            print("✓")
            state.camera = camera
            return True
        else:
            print("⚠ Warning: Camera may not be available")
            state.last_error = "Camera not available"
            state.camera = camera
            return False
    except Exception as e:
        print(f"✗ Failed: {e}")
        state.camera = None
        state.last_error = f"Camera init failed: {e}"
        return False



def start_camera_capture():
    """Background thread to continuously capture frames."""
    if state.camera is None:
        return

    while state.running:
        if state.camera is None:
            time.sleep(0.1)
            continue
        
        try:
            # Grab and retrieve in one go
            ret, frame = state.camera.read()
            if ret:
                state.current_frame = frame
            else:
                time.sleep(0.01)
        except Exception as e:
            state.last_error = f"Camera capture error: {str(e)}"
            time.sleep(0.1)

def generate_frames():
    """MJPEG video stream generator reading from shared state."""
    last_frame_time = 0
    
    while state.running:
        if state.current_frame is None:
            time.sleep(0.1)
            continue
            
        try:
            # Simple frame limiting or just encode always
            # For MJPEG, we can just encode the current frame
            
            # Lower quality = faster encoding = lower latency
            _, buffer = cv2.imencode('.jpg', state.current_frame, [
                cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY,
                cv2.IMWRITE_JPEG_OPTIMIZE, 0
            ])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                   
            # Limit stream FPS slightly to save bandwidth if needed, but 
            # let's keep it max speed for now or rely on client consumption
            time.sleep(0.03) # Approx 30 FPS cap for the stream
            
        except Exception as e:
            state.last_error = f"Stream error: {str(e)}"
            time.sleep(0.05)


def release_camera():
    """Release camera resources."""
    if state.camera:
        try:
            state.camera.release()
            print("✓ Camera released")
        except Exception as e:
            print(f"✗ Camera cleanup error: {e}")
