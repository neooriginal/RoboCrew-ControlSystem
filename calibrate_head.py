#!/usr/bin/env python3
"""
Head Servo Calibration Script
Move the head BY HAND to find safe limits, press Enter to record each position.
Saves limits to a JSON file that servo_controls.py will read.
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'RoboCrew', 'src'))

from config import HEAD_USB
from lerobot.motors import Motor, MotorCalibration, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

HEAD_SERVO_MAP = {"yaw": 7, "pitch": 8}
CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), 'head_limits.json')

def main():
    print("=" * 50)
    print("HEAD SERVO CALIBRATION (Manual Mode)")
    print("=" * 50)
    print()
    print("This script disables torque so you can move the head BY HAND.")
    print("Move gently to find the safe limits, then press Enter to record.")
    print()
    
    # Connect to head servos
    print(f"Connecting to head servos on {HEAD_USB}...")
    
    head_calibration = {
        7: MotorCalibration(id=7, drive_mode=0, homing_offset=0, range_min=0, range_max=4095),
        8: MotorCalibration(id=8, drive_mode=0, homing_offset=0, range_min=0, range_max=4095),
    }
    
    head_bus = FeetechMotorsBus(
        port=HEAD_USB,
        motors={
            HEAD_SERVO_MAP["yaw"]: Motor(HEAD_SERVO_MAP["yaw"], "sts3215", MotorNormMode.DEGREES),
            HEAD_SERVO_MAP["pitch"]: Motor(HEAD_SERVO_MAP["pitch"], "sts3215", MotorNormMode.DEGREES),
        },
        calibration=head_calibration,
    )
    head_bus.connect()
    print("Connected!")
    print()
    
    # Disable torque so user can move by hand
    print("Disabling torque - you can now move the head by hand")
    head_bus.write("Torque_Enable", 7, 0)
    head_bus.write("Torque_Enable", 8, 0)
    print()
    
    def read_positions():
        pos = head_bus.sync_read("Present_Position", [7, 8])
        return round(pos.get(7, 0), 1), round(pos.get(8, 0), 1)
    
    limits = {"yaw_min": 0, "yaw_max": 0, "pitch_min": 0, "pitch_max": 0}
    
    # Step 1: YAW MIN (left)
    print("-" * 40)
    print("STEP 1: YAW MINIMUM (Left limit)")
    print("Move the head as far LEFT as safely possible")
    input("Press ENTER when ready...")
    yaw, pitch = read_positions()
    limits["yaw_min"] = yaw
    print(f"  Recorded yaw_min = {yaw}°")
    print()
    
    # Step 2: YAW MAX (right)
    print("-" * 40)
    print("STEP 2: YAW MAXIMUM (Right limit)")
    print("Move the head as far RIGHT as safely possible")
    input("Press ENTER when ready...")
    yaw, pitch = read_positions()
    limits["yaw_max"] = yaw
    print(f"  Recorded yaw_max = {yaw}°")
    print()
    
    # Step 3: PITCH MIN (up)
    print("-" * 40)
    print("STEP 3: PITCH MINIMUM (Looking up)")
    print("Tilt the head UP as far as safely possible")
    input("Press ENTER when ready...")
    yaw, pitch = read_positions()
    limits["pitch_min"] = pitch
    print(f"  Recorded pitch_min = {pitch}°")
    print()
    
    # Step 4: PITCH MAX (down)
    print("-" * 40)
    print("STEP 4: PITCH MAXIMUM (Looking down)")
    print("Tilt the head DOWN as far as safely possible")
    input("Press ENTER when ready...")
    yaw, pitch = read_positions()
    limits["pitch_max"] = pitch
    print(f"  Recorded pitch_max = {pitch}°")
    print()
    
    # Re-enable torque and center
    print("Re-enabling torque and centering head...")
    head_bus.write("Operating_Mode", 7, 0)  # Position mode
    head_bus.write("Operating_Mode", 8, 0)
    head_bus.enable_torque()
    
    # Move to center
    center_yaw = (limits["yaw_min"] + limits["yaw_max"]) / 2
    center_pitch = (limits["pitch_min"] + limits["pitch_max"]) / 2
    head_bus.sync_write("Goal_Position", {7: center_yaw, 8: center_pitch})
    time.sleep(0.5)
    
    # Save to file
    print()
    print("=" * 50)
    print("CALIBRATION COMPLETE")
    print("=" * 50)
    print()
    print("Limits recorded:")
    print(f"  Yaw:   {limits['yaw_min']}° to {limits['yaw_max']}°")
    print(f"  Pitch: {limits['pitch_min']}° to {limits['pitch_max']}°")
    print()
    
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(limits, f, indent=2)
    print(f"Saved to: {CALIBRATION_FILE}")
    print()
    print("These limits will be automatically enforced by servo_controls.py")
    
    head_bus.disconnect()

if __name__ == "__main__":
    main()
