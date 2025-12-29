"""
RoboCrew Control System - Camera Module
Handles camera initialization and MJPEG streaming.
"""

import time
import cv2
import numpy as np

from config import (
    CAMERA_PORT, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_BUFFER_SIZE,
    STREAM_WIDTH, STREAM_HEIGHT, STREAM_JPEG_QUALITY
)
from state import state


import threading

def init_camera():
    print(f"📷 Connecting camera ({CAMERA_PORT})...", end=" ", flush=True)
    try:
        if state.camera is not None and state.camera.isOpened():
            print("✓ (Already open)")
            return True

        camera = cv2.VideoCapture(CAMERA_PORT)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
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


# Frame synchronization
frame_condition = threading.Condition()
encoded_frame = None

def _capture_loop():
    global encoded_frame
    print("[Camera] Capture thread started")
    
    # Pre-allocate blank frame for fallback
    blank_frame = np.zeros((STREAM_HEIGHT, STREAM_WIDTH, 3), np.uint8)
    cv2.putText(blank_frame, "WAITING...", (20, STREAM_HEIGHT//2), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    _, blank_buffer = cv2.imencode('.jpg', blank_frame, [cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY])
    blank_bytes = blank_buffer.tobytes()
    
    # Set initial encoded frame
    with frame_condition:
        encoded_frame = blank_bytes
        frame_condition.notify_all()

    while state.running and state.camera and state.camera.isOpened():
        try:
            ret, frame = state.camera.read()
            if ret:
                state.latest_frame = frame
                state.frame_id += 1 # New frame captured
                
                # Resize and encode once for all clients
                stream_frame = cv2.resize(frame, (STREAM_WIDTH, STREAM_HEIGHT), interpolation=cv2.INTER_NEAREST)
                _, buffer = cv2.imencode('.jpg', stream_frame, [
                    cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY,
                    cv2.IMWRITE_JPEG_OPTIMIZE, 0
                ])
                
                with frame_condition:
                    encoded_frame = buffer.tobytes()
                    frame_condition.notify_all()
                    
                # Small sleep to limit global framerate if needed (optional)
                # time.sleep(0.01) 
            else:
                time.sleep(0.01)
        except Exception as e:
            print(f"[Camera] Thread error: {e}")
            time.sleep(0.1)
    print("[Camera] Capture thread stopped")


def generate_frames():
    global encoded_frame
    
    # Send current frame immediately to establish connection and prevent
    # "write() before start_response" errors if the camera thread is slow.
    current_frame = encoded_frame
    
    # Fallback if camera hasn't started yet
    if current_frame is None:
        try:
            blank_frame = np.zeros((STREAM_HEIGHT, STREAM_WIDTH, 3), np.uint8)
            cv2.putText(blank_frame, "STARTING...", (20, STREAM_HEIGHT//2), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            _, buffer = cv2.imencode('.jpg', blank_frame, [cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY])
            current_frame = buffer.tobytes()
        except Exception:
            pass # Should not happen, but safe fallback

    if current_frame:
         yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + current_frame + b'\r\n')
    
    while state.running:
        with frame_condition:
            # Wait for notification of NEW frame
            frame_condition.wait(timeout=0.5)
            current_frame = encoded_frame

        if current_frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + current_frame + b'\r\n')
        else:
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
