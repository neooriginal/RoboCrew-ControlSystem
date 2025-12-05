"""
RoboCrew Control System - Configuration
"""

# Hardware ports
CAMERA_PORT = "/dev/video0"
WHEEL_USB = "/dev/robot_acm0"  # Also has arm motors (IDs 1-6) + wheels (IDs 7-9)
HEAD_USB = "/dev/robot_acm1"

# Arm calibration file path (relative to project root)
ARM_CALIBRATION_PATH = "RoboCrew/calibrations/robot_arms.json"

# Web server
WEB_PORT = 5000

# Camera settings
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_BUFFER_SIZE = 1
JPEG_QUALITY = 50

# Control settings
MOVEMENT_LOOP_INTERVAL = 0.05  # 50ms between movement updates
HEAD_UPDATE_INTERVAL = 33  # ~30 updates/sec for smooth control
ARM_UPDATE_INTERVAL = 50  # ~20 updates/sec for arm control

# Arm control sensitivity
ARM_XY_SENSITIVITY = 0.5  # Degrees per pixel of mouse movement
ARM_WRIST_SENSITIVITY = 2.0  # Degrees per scroll unit
ARM_SHOULDER_PAN_STEP = 5.0  # Degrees per keypress
ARM_WRIST_FLEX_STEP = 5.0  # Degrees per keypress
