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

# DEBUG: Latency diagnostics (temporary)
DEBUG_LATENCY = True
_capture_times = []
_encode_times = []
_last_fps_log = 0
_frame_timestamps = {}  # frame_id -> timestamp when captured


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
current_frame_id = 0  # Track which frame is currently encoded

def _capture_loop():
    global encoded_frame, current_frame_id, _last_fps_log, _capture_times, _encode_times, _frame_timestamps
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
    
    last_capture_time = time.time()

    while state.running and state.camera and state.camera.isOpened():
        try:
            capture_start = time.time()
            ret, frame = state.camera.read()
            capture_time = time.time() - capture_start
            
            if ret:
                state.latest_frame = frame
                state.frame_id += 1
                
                # DEBUG: Track capture timing
                if DEBUG_LATENCY:
                    _capture_times.append(capture_time)
                    _frame_timestamps[state.frame_id] = time.time()
                    # Cleanup old timestamps
                    if len(_frame_timestamps) > 100:
                        old_ids = list(_frame_timestamps.keys())[:-50]
                        for old_id in old_ids:
                            _frame_timestamps.pop(old_id, None)
                
                # Resize and encode once for all clients
                encode_start = time.time()
                stream_frame = cv2.resize(frame, (STREAM_WIDTH, STREAM_HEIGHT), interpolation=cv2.INTER_NEAREST)
                _, buffer = cv2.imencode('.jpg', stream_frame, [
                    cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY,
                    cv2.IMWRITE_JPEG_OPTIMIZE, 0
                ])
                encode_time = time.time() - encode_start
                
                if DEBUG_LATENCY:
                    _encode_times.append(encode_time)
                
                with frame_condition:
                    encoded_frame = buffer.tobytes()
                    current_frame_id = state.frame_id
                    frame_condition.notify_all()
                
                # DEBUG: Log FPS every 3 seconds
                if DEBUG_LATENCY and time.time() - _last_fps_log > 3:
                    now = time.time()
                    fps = 1.0 / (now - last_capture_time) if (now - last_capture_time) > 0 else 0
                    avg_capture = sum(_capture_times[-30:]) / max(len(_capture_times[-30:]), 1) * 1000
                    avg_encode = sum(_encode_times[-30:]) / max(len(_encode_times[-30:]), 1) * 1000
                    frame_size_kb = len(buffer) / 1024
                    print(f"[LATENCY] FPS: {fps:.1f} | Capture: {avg_capture:.1f}ms | Encode: {avg_encode:.1f}ms | Size: {frame_size_kb:.1f}KB")
                    _last_fps_log = now
                
                last_capture_time = time.time()
            else:
                time.sleep(0.01)
        except Exception as e:
            print(f"[Camera] Thread error: {e}")
            time.sleep(0.1)
    print("[Camera] Capture thread stopped")


def generate_frames():
    global encoded_frame, current_frame_id, _frame_timestamps
    
    # Send current frame immediately to establish connection and prevent
    # "write() before start_response" errors if the camera thread is slow.
    current_frame = encoded_frame
    last_sent_frame_id = 0
    frames_sent = 0
    gen_start_time = time.time()
    
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
         frames_sent += 1
    
    while state.running:
        with frame_condition:
            # Wait for notification of NEW frame - reduced timeout for lower latency
            frame_condition.wait(timeout=0.05)  # 50ms max wait instead of 500ms
            
            # Skip if this is the same frame we already sent
            if current_frame_id == last_sent_frame_id:
                continue
            
            current_frame = encoded_frame
            last_sent_frame_id = current_frame_id

        if current_frame:
            # DEBUG: Measure stream latency
            if DEBUG_LATENCY and last_sent_frame_id in _frame_timestamps:
                stream_latency = (time.time() - _frame_timestamps[last_sent_frame_id]) * 1000
                if frames_sent % 30 == 0:  # Log every 30 frames
                    elapsed = time.time() - gen_start_time
                    effective_fps = frames_sent / elapsed if elapsed > 0 else 0
                    print(f"[STREAM] Latency: {stream_latency:.1f}ms | Effective FPS: {effective_fps:.1f}")
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + current_frame + b'\r\n')
            frames_sent += 1
        else:
            time.sleep(0.01)  # Reduced from 0.1


def release_camera():
    """Release camera resources."""
    if state.camera:
        try:
            state.camera.release()
            print("✓ Camera released")
        except Exception as e:
            print(f"✗ Camera cleanup error: {e}")
    state.camera = None
