"""ARCS Configuration"""

from pathlib import Path

# Hardware ports
CAMERA_PORT = "/dev/video0"
WHEEL_USB = "/dev/robot_acm0"
HEAD_USB = "/dev/robot_acm1"

# Web server
WEB_PORT = 5000

# Camera
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_BUFFER_SIZE = 1
JPEG_QUALITY = 50

# Control intervals (ms)
MOVEMENT_LOOP_INTERVAL = 0.05
HEAD_UPDATE_INTERVAL = 33
ARM_UPDATE_INTERVAL = 50

# Arm control sensitivity
ARM_XY_SENSITIVITY = 0.1
ARM_WRIST_SENSITIVITY = 1.0
ARM_SHOULDER_PAN_STEP = 2.0
ARM_WRIST_FLEX_STEP = 2.0

# Safety
REMOTE_TIMEOUT = 0.5
AI_MIN_BRIGHTNESS = 40
STALL_LOAD_THRESHOLD = 600
STALL_CHECK_INTERVAL = 0.5

# Text-to-Speech
TTS_ENABLED = True
TTS_AUDIO_DEVICE = "plughw:1,0"  # ALSA device (plughw:1,0 = HDMI 1)
TTS_TLD = "com"  # Google TLD for voice variant (com, co.uk, com.au, etc.)

# VR Control
VR_ENABLED = True
VR_WEBSOCKET_PORT = 8442
VR_TO_ROBOT_SCALE = 1.0
VR_SEND_INTERVAL = 0.05
VR_A_BUTTON_DEBOUNCE = 0.5  # Seconds to prevent accidental double-clicks

# VLA Training Configuration
VLA_ARM_CAMERA_PORT = "/dev/video1"     # Arm-mounted camera
VLA_CAMERA_WIDTH = 320                  # Reduced resolution for Pi 4 performance
VLA_CAMERA_HEIGHT = 240
VLA_CAMERA_FPS = 30
VLA_DATASETS_DIR = Path.home() / ".cache" / "huggingface" / "lerobot" / "datasets"
VLA_MODELS_DIR = Path("./models/vla")
VLA_DEFAULT_POLICY = "act"
VLA_TRAINING_DEVICE = "cpu"             # Force CPU for Pi 4

