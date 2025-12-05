"""
RoboCrew Control System - Arm Control Module
Handles arm movement with direct joint control.
"""

from state import state
from config import (
    ARM_XY_SENSITIVITY,
    ARM_WRIST_SENSITIVITY,
    ARM_SHOULDER_PAN_STEP,
    ARM_WRIST_FLEX_STEP,
)

# Step size for elbow control
ARM_ELBOW_STEP = 2.0


class ArmController:
    """
    Arm controller with direct joint control.
    
    Controls:
    - Mouse X → shoulder_pan (rotate base left/right)
    - Mouse Y → shoulder_lift (tilt arm up/down)
    - Mouse wheel → wrist_roll
    - Q/E → shoulder_pan (fine tune)
    - R/F → wrist_flex
    - T/G → elbow_flex (NEW)
    - Mouse click → gripper
    """
    
    def __init__(self):
        # Current target positions
        self.targets = {
            'shoulder_pan': 0,
            'shoulder_lift': 0,
            'elbow_flex': 0,
            'wrist_flex': 0,
            'wrist_roll': 0,
            'gripper': 90  # Open
        }
    
    def reset_to_home(self):
        """Reset arm to home position."""
        self.targets = {
            'shoulder_pan': 0,
            'shoulder_lift': 0,
            'elbow_flex': 0,
            'wrist_flex': 0,
            'wrist_roll': 0,
            'gripper': 90
        }
        return self.targets.copy()
    
    def handle_mouse_move(self, delta_x, delta_y):
        """
        Handle mouse movement to control arm position.
        
        Mouse X → shoulder_pan
        Mouse Y → shoulder_lift
        
        Does NOT touch elbow_flex or wrist_flex - those are keyboard only.
        """
        # Mouse X controls shoulder_pan (base rotation)
        self.targets['shoulder_pan'] += delta_x * ARM_XY_SENSITIVITY
        self.targets['shoulder_pan'] = max(-90, min(90, self.targets['shoulder_pan']))
        
        # Mouse Y controls shoulder_lift (arm tilt)
        self.targets['shoulder_lift'] += delta_y * ARM_XY_SENSITIVITY
        self.targets['shoulder_lift'] = max(-90, min(90, self.targets['shoulder_lift']))
        
        return self.targets.copy()
    
    def handle_scroll(self, delta):
        """Handle mouse scroll to control wrist roll."""
        self.targets['wrist_roll'] += delta * ARM_WRIST_SENSITIVITY
        self.targets['wrist_roll'] = max(-150, min(150, self.targets['wrist_roll']))
        return self.targets['wrist_roll']
    
    def handle_shoulder_pan(self, direction):
        """Handle keyboard Q/E for shoulder pan."""
        self.targets['shoulder_pan'] += direction * ARM_SHOULDER_PAN_STEP
        self.targets['shoulder_pan'] = max(-90, min(90, self.targets['shoulder_pan']))
        return self.targets['shoulder_pan']
    
    def handle_wrist_flex(self, direction):
        """Handle keyboard R/F for wrist flex."""
        self.targets['wrist_flex'] += direction * ARM_WRIST_FLEX_STEP
        self.targets['wrist_flex'] = max(-90, min(90, self.targets['wrist_flex']))
        return self.targets['wrist_flex']
    
    def handle_elbow_flex(self, direction):
        """Handle keyboard T/G for elbow flex."""
        self.targets['elbow_flex'] += direction * ARM_ELBOW_STEP
        self.targets['elbow_flex'] = max(-90, min(90, self.targets['elbow_flex']))
        return self.targets['elbow_flex']
    
    def set_gripper(self, closed):
        """Set gripper state."""
        self.targets['gripper'] = 2 if closed else 90  # 2 = closed, 90 = open
        return self.targets['gripper']
    
    def get_targets(self):
        """Get current target positions."""
        return self.targets.copy()
    
    def set_from_current(self, positions):
        """Initialize targets from current arm positions."""
        for joint, angle in positions.items():
            if joint in self.targets:
                self.targets[joint] = angle


# Global arm controller instance
arm_controller = ArmController()
