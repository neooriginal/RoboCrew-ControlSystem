"""
RoboCrew Control System - Movement Control
Handles wheel movement commands and the continuous movement loop.
"""

import time
from config import MOVEMENT_LOOP_INTERVAL
from state import state

# Safety timeout - stop if no movement command received within this time (seconds)
MOVEMENT_TIMEOUT = 0.5


def execute_movement(movement):
    """
    Execute a movement command based on the movement state dict.
    Returns True if successful, False otherwise.
    """
    if state.controller is None:
        return False
    
    try:
        if movement.get('forward'):
            state.controller._wheels_write('up')
        elif movement.get('backward'):
            state.controller._wheels_write('down')
        elif movement.get('left'):
            state.controller._wheels_write('left')
        elif movement.get('right'):
            state.controller._wheels_write('right')
        else:
            state.controller._wheels_stop()
        return True
    except Exception as e:
        state.last_error = f"Movement error: {str(e)}"
        return False


def movement_loop():
    """
    Continuous movement control thread.
    Keeps wheels moving while key is held.
    Includes dead man's switch - auto-stops if no command received within timeout.
    """
    while state.running:
        if state.controller is None:
            time.sleep(0.1)
            continue
        
        movement = state.get_movement()
        
        # Safety timeout: if any movement is active but we haven't received
        # a command recently, stop everything (dead man's switch)
        if any(movement.values()):
            time_since_command = time.time() - state.last_movement_command
            if time_since_command > MOVEMENT_TIMEOUT:
                # Connection lost or key release missed - stop immediately
                state.stop_all_movement()
                movement = {'forward': False, 'backward': False, 'left': False, 'right': False}
        
        try:
            execute_movement(movement)
        except Exception as e:
            state.last_error = f"Movement loop error: {str(e)}"
        
        time.sleep(MOVEMENT_LOOP_INTERVAL)


def stop_movement():
    """Stop all wheel movement."""
    if state.controller:
        try:
            state.controller._wheels_stop()
        except Exception as e:
            state.last_error = f"Stop movement error: {str(e)}"
