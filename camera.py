"""
RoboCrew Control System - Camera Module
Handles camera initialization and MJPEG streaming.
"""

import time
import cv2
import threading
import atexit

from config import CAMERA_PORT, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_BUFFER_SIZE, JPEG_QUALITY
from state import state


class ThreadedCamera:
    """
    Continuously captures frames in a separate thread to prevent IO blocking.
    This ensures the latest frame is always available for AI and Streaming.
    """
    def __init__(self, src=0):
        self.src = src
        self.cap = cv2.VideoCapture(self.src)
        
        # Configure for low latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, CAMERA_BUFFER_SIZE)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        
        self.grabbed, self.frame = self.cap.read()
        self.started = False
        self.read_lock = threading.Lock()
        self.stop_signal = False

    def start(self):
        if self.started:
            return self
        self.started = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()
        return self

    def update(self):
        while self.started:
            if self.stop_signal:
                break
            grabbed, frame = self.cap.read()
            with self.read_lock:
                self.grabbed = grabbed
                self.frame = frame
            # IO is blocking, so no sleep needed here, it waits for frame naturally in hardware

    def read(self):
        with self.read_lock:
            if self.grabbed:
                return True, self.frame.copy()
            return False, None

    def release(self):
        self.started = False
        self.stop_signal = True
        try:
            self.thread.join(timeout=1.0)
        except:
            pass
        self.cap.release()

# Global camera instance
threaded_camera = None

def init_camera():
    """Initialize the threaded camera."""
    global threaded_camera
    print(f"📷 Connecting camera ({CAMERA_PORT})...", end=" ", flush=True)
    
    try:
        if threaded_camera is not None:
             threaded_camera.release()
             
        threaded_camera = ThreadedCamera(CAMERA_PORT)
        if threaded_camera.grabbed:
            threaded_camera.start()
            print("✓")
            # We also set state.camera to the threaded instance for compatibility, 
            # though other modules should be careful about using standard cv2 calls on it if they expect a raw VideoCapture.
            # Ideally, they should use read() which matches the API.
            state.camera = threaded_camera 
            return True
        else:
            print("⚠ Warning: Camera opened but returned no frame")
            threaded_camera.release()
            state.camera = None
            state.last_error = "Camera no frame"
            return False
            
    except Exception as e:
        print(f"✗ Failed: {e}")
        state.camera = None
        state.last_error = f"Camera init failed: {e}"
        return False


def generate_frames():
    """MJPEG video stream generator using threaded capture."""
    while state.running:
        if state.camera is None:
            time.sleep(0.5)
            # Try to reconnect
            if not init_camera():
                continue
        
        try:
            # Get latest frame non-blocking
            ret, frame = state.camera.read()
            
            if not ret or frame is None:
                time.sleep(0.01)
                continue
            
            # Resize for efficient streaming (960x540 qHD) while keeping capture high-res for AI
            # Using INTER_LINEAR is slightly slower than NEAREST but looks much better. 
            # Given we are now threaded, we can afford the tiny cost.
            stream_frame = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_LINEAR)

            # Encode
            _, buffer = cv2.imencode('.jpg', stream_frame, [
                cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY,
                cv2.IMWRITE_JPEG_OPTIMIZE, 0
            ])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            # Adding a tiny sleep controls the max framerate to avoid flooding the network
            # 0.03 ~= 30 FPS
            time.sleep(0.02)
            
        except Exception as e:
            state.last_error = f"Camera error: {str(e)}"
            time.sleep(0.1)


def release_camera():
    """Release camera resources."""
    global threaded_camera
    if threaded_camera:
        try:
            threaded_camera.release()
            state.camera = None
            print("✓ Camera released")
        except Exception as e:
            print(f"✗ Camera cleanup error: {e}")
