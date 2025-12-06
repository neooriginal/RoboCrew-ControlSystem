#!/usr/bin/env python3
"""Servo calibration script for XLeRobot arm motors.

Usage:
    python calibrate.py [output_file]

The script will:
1. Connect to the servo bus with torque disabled (so you can manually move motors)
2. Guide you through calibrating each motor's min, max, and home positions
3. Save the calibration to a JSON file
"""

import sys
import os
import json
from pathlib import Path

# Add local RoboCrew source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'RoboCrew', 'src'))

from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.motors import Motor, MotorNormMode

# Configuration
USB_PORT = "/dev/robot_acm0"
DEFAULT_OUTPUT = "RoboCrew/calibrations/robot_arms.json"

# Motor definitions (same as servo_controls.py)
ARM_MOTORS = {
    "shoulder_pan": 1,
    "shoulder_lift": 2,
    "elbow_flex": 3,
    "wrist_flex": 4,
    "wrist_roll": 5,
    "gripper": 6,
}


def read_position(bus, motor_id):
    """Read raw position from a motor."""
    try:
        # Use sync_read which returns actual values
        result = bus.sync_read("Present_Position", [motor_id])
        pos = result.get(motor_id)
        if pos is not None:
            return int(pos)
        print(f"  No position returned for motor {motor_id}")
        return None
    except Exception as e:
        print(f"  Error reading motor {motor_id}: {e}")
        return None


def wait_for_keypress(prompt):
    """Wait for user to press Enter."""
    input(prompt)


def calibrate_motor(bus, name, motor_id):
    """Calibrate a single motor by recording min, max, and home positions."""
    print(f"\n{'='*50}")
    print(f"Calibrating: {name} (Motor ID: {motor_id})")
    print(f"{'='*50}")
    
    # Read current position
    current = read_position(bus, motor_id)
    if current is not None:
        print(f"Current position: {current}")
    
    # Get MIN position
    print(f"\n[MIN] Move the {name} to its MINIMUM position (one extreme)")
    print("      This is the lowest angle/most retracted position")
    wait_for_keypress("      Press Enter when ready...")
    range_min = read_position(bus, motor_id)
    if range_min is None:
        return None
    print(f"      Recorded MIN: {range_min}")
    
    # Get MAX position
    print(f"\n[MAX] Move the {name} to its MAXIMUM position (other extreme)")
    print("      This is the highest angle/most extended position")
    wait_for_keypress("      Press Enter when ready...")
    range_max = read_position(bus, motor_id)
    if range_max is None:
        return None
    print(f"      Recorded MAX: {range_max}")
    
    # Ensure min < max
    if range_min > range_max:
        range_min, range_max = range_max, range_min
        print(f"      (Swapped min/max so min < max)")
    
    # Get HOME position
    print(f"\n[HOME] Move the {name} to its HOME/ZERO position")
    print("       This is typically the neutral/resting position")
    wait_for_keypress("       Press Enter when ready...")
    homing_offset = read_position(bus, motor_id)
    if homing_offset is None:
        return None
    print(f"       Recorded HOME: {homing_offset}")
    
    return {
        "id": motor_id,
        "drive_mode": 0,
        "homing_offset": homing_offset,
        "range_min": range_min,
        "range_max": range_max,
    }


def live_position_monitor(bus, motor_ids):
    """Continuously show positions of all motors until user presses Enter."""
    import select
    import threading
    
    stop_event = threading.Event()
    
    def input_thread():
        input()
        stop_event.set()
    
    thread = threading.Thread(target=input_thread, daemon=True)
    thread.start()
    
    print("\nLive position monitor (press Enter to stop):")
    print("-" * 50)
    
    while not stop_event.is_set():
        positions = []
        for name, motor_id in motor_ids.items():
            pos = read_position(bus, motor_id)
            if pos is not None:
                positions.append(f"{name[:8]:>8}={pos:4d}")
        
        print(f"\r{' | '.join(positions)}", end="", flush=True)
        
        import time
        time.sleep(0.1)
    
    print("\n")


def main():
    output_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    output_path = Path(output_file)
    
    print("=" * 60)
    print("🔧 XLeRobot Arm Calibration Script")
    print("=" * 60)
    print(f"\nOutput file: {output_path.absolute()}")
    print(f"USB port: {USB_PORT}")
    print(f"\nMotors to calibrate:")
    for name, motor_id in ARM_MOTORS.items():
        print(f"  {motor_id}: {name}")
    
    # Load existing calibration if present
    existing_cal = {}
    if output_path.exists():
        try:
            with open(output_path) as f:
                existing_cal = json.load(f)
            print(f"\nExisting calibration found with {len(existing_cal)} motors")
        except Exception as e:
            print(f"\nCould not load existing calibration: {e}")
    
    # Connect to bus with torque disabled
    print("\n" + "-" * 60)
    print("Connecting to servo bus...")
    
    try:
        motors = {motor_id: Motor(motor_id, "sts3215", MotorNormMode.RANGE_M100_100) 
                  for motor_id in ARM_MOTORS.values()}
        bus = FeetechMotorsBus(port=USB_PORT, motors=motors)
        bus.connect()
        print("Connected!")
        
        # Disable torque so user can manually move motors
        print("Disabling torque (you can now manually move the motors)...")
        bus.disable_torque()
        print("Torque disabled ✓")
        
    except Exception as e:
        print(f"Failed to connect: {e}")
        return 1
    
    try:
        # Menu
        while True:
            print("\n" + "=" * 60)
            print("Options:")
            print("  1. Calibrate all motors")
            print("  2. Calibrate specific motor")
            print("  3. Live position monitor")
            print("  4. Save and exit")
            print("  5. Exit without saving")
            print("=" * 60)
            
            choice = input("Choose option (1-5): ").strip()
            
            if choice == "1":
                # Calibrate all motors
                calibration = {}
                for name, motor_id in ARM_MOTORS.items():
                    result = calibrate_motor(bus, name, motor_id)
                    if result:
                        calibration[name] = result
                        existing_cal[name] = result
                    else:
                        print(f"Skipping {name} due to error")
                
                print(f"\nCalibrated {len(calibration)} motors")
                
            elif choice == "2":
                # Calibrate specific motor
                print("\nAvailable motors:")
                for i, (name, motor_id) in enumerate(ARM_MOTORS.items(), 1):
                    print(f"  {i}. {name} (ID: {motor_id})")
                
                try:
                    idx = int(input("Enter motor number: ")) - 1
                    name = list(ARM_MOTORS.keys())[idx]
                    motor_id = ARM_MOTORS[name]
                    result = calibrate_motor(bus, name, motor_id)
                    if result:
                        existing_cal[name] = result
                        print(f"\nCalibration for {name} updated")
                except (ValueError, IndexError):
                    print("Invalid selection")
                    
            elif choice == "3":
                # Live position monitor
                live_position_monitor(bus, ARM_MOTORS)
                
            elif choice == "4":
                # Save and exit
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    json.dump(existing_cal, f, indent=4)
                print(f"\n✓ Saved calibration to {output_path}")
                break
                
            elif choice == "5":
                # Exit without saving
                print("\nExiting without saving")
                break
                
            else:
                print("Invalid option")
        
    finally:
        print("\nDisconnecting...")
        bus.disconnect()
        print("Done!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
