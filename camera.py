"""
RoboCrew Control System - Camera Module
Handles camera initialization and MJPEG streaming.
"""

import time
import cv2
import numpy as np
import threading

from config import (
    CAMERA_PORT, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_BUFFER_SIZE,
    STREAM_WIDTH, STREAM_HEIGHT, STREAM_JPEG_QUALITY
)
from state import state


def init_camera():
    print(f"📷 Connecting camera ({CAMERA_PORT})...", end=" ", flush=True)
    try:
        if state.camera is not None and state.camera.isOpened():
            print("✓ (Already open)")
            return True

        # Use V4L2 backend for better buffer control on Linux
        camera = cv2.VideoCapture(CAMERA_PORT, cv2.CAP_V4L2)
        
        # Request MJPEG format (hardware-encoded, faster)
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        camera.set(cv2.CAP_PROP_FPS, 30)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if camera.isOpened():
            # Drain stale frames from buffer
            for _ in range(5):
                camera.grab()
            
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
current_frame_id = 0


def _capture_loop():
    global encoded_frame, current_frame_id
    print("[Camera] Capture thread started")
    
    # Pre-allocate blank frame for fallback
    blank_frame = np.zeros((STREAM_HEIGHT, STREAM_WIDTH, 3), np.uint8)
    cv2.putText(blank_frame, "WAITING...", (20, STREAM_HEIGHT//2), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    _, blank_buffer = cv2.imencode('.jpg', blank_frame, [cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY])
    blank_bytes = blank_buffer.tobytes()
    
    with frame_condition:
        encoded_frame = blank_bytes
        frame_condition.notify_all()

    while state.running and state.camera and state.camera.isOpened():
        try:
            # Non-blocking capture: grab() + retrieve() instead of read()
            grabbed = state.camera.grab()
            if grabbed:
                ret, frame = state.camera.retrieve()
            else:
                ret = False
                frame = None
            
            if ret and frame is not None:
                state.latest_frame = frame
                state.frame_id += 1
                
                # Resize and encode for streaming
                stream_frame = cv2.resize(frame, (STREAM_WIDTH, STREAM_HEIGHT), interpolation=cv2.INTER_NEAREST)
                _, buffer = cv2.imencode('.jpg', stream_frame, [
                    cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY,
                    cv2.IMWRITE_JPEG_OPTIMIZE, 0
                ])
                
                with frame_condition:
                    encoded_frame = buffer.tobytes()
                    current_frame_id = state.frame_id
                    frame_condition.notify_all()
            else:
                time.sleep(0.01)
        except Exception as e:
            print(f"[Camera] Thread error: {e}")
            time.sleep(0.1)
    print("[Camera] Capture thread stopped")


def generate_frames():
    global encoded_frame, current_frame_id
    
    current_frame = encoded_frame
    last_sent_frame_id = 0
    
    # Fallback if camera hasn't started yet
    if current_frame is None:
        try:
            blank_frame = np.zeros((STREAM_HEIGHT, STREAM_WIDTH, 3), np.uint8)
            cv2.putText(blank_frame, "STARTING...", (20, STREAM_HEIGHT//2), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            _, buffer = cv2.imencode('.jpg', blank_frame, [cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY])
            current_frame = buffer.tobytes()
        except Exception:
            pass

    if current_frame:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + current_frame + b'\r\n')
    
    while state.running:
        with frame_condition:
            frame_condition.wait(timeout=0.05)
            
            if current_frame_id == last_sent_frame_id:
                continue
            
            current_frame = encoded_frame
            last_sent_frame_id = current_frame_id

        if current_frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + current_frame + b'\r\n')
        else:
            time.sleep(0.01)


def release_camera():
    """Release camera resources."""
    if state.camera:
        try:
            state.camera.release()
            print("✓ Camera released")
        except Exception as e:
            print(f"✗ Camera cleanup error: {e}")
    state.camera = None
