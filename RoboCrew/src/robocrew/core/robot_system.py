import threading
import time
import cv2
import logging
import glob
from typing import Optional, Dict, Any, Tuple

from state import state
from robocrew.robots.XLeRobot.servo_controls import ServoControler
from config import WHEEL_USB, HEAD_USB, CAMERA_PORT, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_BUFFER_SIZE

logger = logging.getLogger(__name__)

class RobotSystem:
    """
    Central management for RoboCrew hardware and state.
    Handles Servos, Camera, and shared State.
    """
    def __init__(self):
        self.controller: Optional[ServoControler] = None
        self.camera = None
        self.camera_lock = threading.Lock()
        self.running = True
        
        # Initialize hardware
        self._init_camera()
        self._init_servos()
        
        state.robot_system = self
        
    def _init_camera(self):
        """Initialize the camera."""
        try:
            self.camera = cv2.VideoCapture(CAMERA_PORT)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, CAMERA_BUFFER_SIZE)
            if not self.camera.isOpened():
                logger.error(f"Failed to open camera on {CAMERA_PORT}")
                self.camera = None
            else:
                logger.info(f"Camera initialized on {CAMERA_PORT}")
            state.camera = self.camera
        except Exception as e:
            logger.error(f"Camera init error: {e}")
            self.camera = None
            state.camera = None

    def _detect_serial_ports(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Scan for connected serial ports and identify which is Wheel/Arm and which is Head.
        Returns: (wheel_port, head_port)
        """
        # Candidate ports
        ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/robot_acm*')
        # Filter duplicates (e.g. symlinks) - prioritized /dev/robot_acm if available? 
        # Actually set makes them unique but we want to prefer robot_acm if it works.
        # Simple unique list:
        ports = sorted(list(set(ports)))
        
        logger.info(f"Scanning ports: {ports}")
        
        wheel_port = None
        head_port = None
        
        # Identification Logic:
        # Wheel/Arm bus has ID 9 (Wheel) and ID 1 (Arm).
        # Head bus has ID 7 and 8 (Head) ONLY (conceptually).
        # Caveat: IDs 7 and 8 are ALSO on the Wheel bus (Left/Right Rear wheels?).
        # Wait, if 7/8 are on BOTH, we must distinguish by finding 9 or 1 first.
        # If a port has 9 or 1 -> IT IS THE WHEEL BUS.
        # If a port DOES NOT have 9/1 but HAS 7 or 8 -> IT IS THE HEAD BUS.
        
        from lerobot.motors.feetech import FeetechMotorsBus
        from lerobot.motors import Motor, MotorNormMode
        
        for port in ports:
            try:
                logger.info(f"Checking port {port}...")
                
                # Check for Marker ID 9 (Rear Wheel) or 1 (Shoulder)
                # We need to init bus to check.
                # Use a dummy motor config to probe.
                
                # Probe for Wheel/Arm (ID 9)
                probe_motor_id = 9
                bus = FeetechMotorsBus(
                    port=port,
                    motors={probe_motor_id: Motor(probe_motor_id, "sts3215", MotorNormMode.DEGREES)}
                )
                bus.connect()
                
                # Try to read position
                try:
                    pos = bus.read("Present_Position", probe_motor_id)
                    if pos is not None:
                        logger.info(f"  -> Found Motor {probe_motor_id} on {port}. This is WHEEL/ARM bus.")
                        wheel_port = port
                        bus.disconnect()
                        continue
                except:
                    pass
                
                bus.disconnect()
                
                # Probe for Head (ID 7) - IF it wasn't Wheel bus
                # Setup probing for 7
                probe_motor_id = 7
                bus = FeetechMotorsBus(
                    port=port,
                    motors={probe_motor_id: Motor(probe_motor_id, "sts3215", MotorNormMode.DEGREES)}
                )
                bus.connect()
                try:
                    pos = bus.read("Present_Position", probe_motor_id)
                    if pos is not None:
                         logger.info(f"  -> Found Motor {probe_motor_id} on {port} (and not 9). This is HEAD bus.")
                         head_port = port
                except:
                    pass
                
                bus.disconnect()
                
            except Exception as e:
                logger.warning(f"  -> Port {port} check failed: {e}")
                
        return wheel_port, head_port

    def _init_servos(self):
        """Initialize servo controller."""
        
        # 1. Detect Ports
        if WHEEL_USB is None or HEAD_USB is None:
            logger.info("Auto-detecting ports...")
            detected_wheel, detected_head = self._detect_serial_ports()
            
            wheel_port = WHEEL_USB or detected_wheel
            head_port = HEAD_USB or detected_head
        else:
            wheel_port = WHEEL_USB
            head_port = HEAD_USB

        if not wheel_port or not head_port:
             logger.error(f"Failed to identify ports! Wheel={wheel_port}, Head={head_port}")
             state.last_error = "Port Detection Failed"
             return

        logger.info(f"Connecting servos (Wheel={wheel_port}, Head={head_port})...")
        try:
            self.controller = ServoControler(
                wheel_port, 
                head_port,
                enable_arm=True
            )
            state.controller = self.controller
            
            # Initial readings
            if self.controller.arm_enabled:
                state.arm_connected = True
                try:
                    pos = self.controller.get_arm_position()
                    state.update_arm_positions(pos)
                except Exception as e:
                    logger.warning(f"Could not read arm: {e}")
            
            try:
                pos = self.controller.get_head_position()
                state.head_yaw = round(pos.get(7, 0), 1)
                state.head_pitch = round(pos.get(8, 0), 1)
            except Exception as e:
                logger.warning(f"Could not read head: {e}")
                
            logger.info("Servos connected successfully")
        except Exception as e:
            logger.error(f"Servo connection failed: {e}")
            state.last_error = str(e)
            self.controller = None

    def get_frame(self):
        """Thread-safe frame capture."""
        if not self.camera:
            return None
        with self.camera_lock:
            ret, frame = self.camera.read()
            if ret:
                return frame
            return None

    def cleanup(self):
        """Release resources."""
        self.running = False
        if self.controller:
            try:
                self.controller.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting servos: {e}")
        
        if self.camera:
            self.camera.release()
            
    def emergency_stop(self):
        """Immediate stop of all movement."""
        if self.controller:
            # Stop wheels
            self.controller._wheels_stop()
            # We might want to relax arm or hold position depending on safety
            # For now, just stopping wheels is critical
