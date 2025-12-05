"""
RoboCrew Control System - Flask Routes
Blueprint containing all HTTP endpoints.
"""

from flask import Blueprint, Response, jsonify, request, render_template

from state import state
from camera import generate_frames
from movement import execute_movement
from arm import arm_controller

# Create blueprint
bp = Blueprint('robot', __name__)


@bp.route('/')
def index():
    """Serve the main control interface."""
    return render_template('index.html')


@bp.route('/status')
def get_status():
    """Get connection status for debugging."""
    return jsonify({
        'controller_connected': state.controller is not None,
        'camera_connected': state.camera is not None and state.camera.isOpened(),
        'arm_connected': state.arm_connected,
        'control_mode': state.get_control_mode(),
        'head_yaw': state.head_yaw,
        'head_pitch': state.head_pitch,
        'movement': state.movement,
        'arm_positions': state.get_arm_positions(),
        'error': state.last_error
    })


@bp.route('/video_feed')
def video_feed():
    """MJPEG video stream endpoint."""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@bp.route('/head_position')
def get_head_position():
    """Get current head servo positions - read fresh from servos."""
    if state.controller is None:
        return jsonify({'error': 'No controller connected'})
    
    try:
        pos = state.controller.get_head_position()
        print(f"[HEAD READ] Raw position from servos: {pos}")
        yaw = round(pos.get(7, 0), 1)
        pitch = round(pos.get(8, 0), 1)
        print(f"[HEAD READ] Parsed: yaw={yaw}, pitch={pitch}")
        
        # Update cached values
        state.head_yaw = yaw
        state.head_pitch = pitch
        return jsonify({'yaw': yaw, 'pitch': pitch})
    except Exception as e:
        state.last_error = f"Head read error: {str(e)}"
        print(f"[HEAD READ ERROR] {e}")
        return jsonify({'error': str(e)})


@bp.route('/head', methods=['POST'])
def set_head():
    """Set head yaw and pitch - smooth incremental control."""
    if state.controller is None:
        return jsonify({'status': 'error', 'error': 'No controller connected'})
    
    data = request.json
    yaw = float(data.get('yaw', state.head_yaw))
    pitch = float(data.get('pitch', state.head_pitch))
    
    print(f"[HEAD WRITE] Commanding: yaw={yaw}, pitch={pitch}")
    
    try:
        state.controller.turn_head_yaw(yaw)
        state.controller.turn_head_pitch(pitch)
        state.head_yaw = yaw
        state.head_pitch = pitch
        return jsonify({'status': 'ok', 'yaw': yaw, 'pitch': pitch})
    except Exception as e:
        state.last_error = f"Head write error: {str(e)}"
        print(f"[HEAD WRITE ERROR] {e}")
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/move', methods=['POST'])
def move():
    """Update movement state from WASD keys."""
    if state.controller is None:
        return jsonify({'status': 'error', 'error': 'No controller connected'})
    
    data = request.json
    state.update_movement(data)
    
    # Execute movement immediately for responsiveness
    movement = state.get_movement()
    success = execute_movement(movement)
    
    if success:
        return jsonify({'status': 'ok'})
    else:
        return jsonify({'status': 'error', 'error': state.last_error})


# ============== Control Mode ==============

@bp.route('/mode', methods=['GET'])
def get_mode():
    """Get current control mode."""
    return jsonify({'mode': state.get_control_mode()})


@bp.route('/mode', methods=['POST'])
def set_mode():
    """Set control mode ('drive' or 'arm')."""
    data = request.json
    mode = data.get('mode', 'drive')
    
    if state.set_control_mode(mode):
        print(f"[MODE] Switched to: {mode}")
        return jsonify({'status': 'ok', 'mode': mode})
    else:
        return jsonify({'status': 'error', 'error': f'Invalid mode: {mode}'})


# ============== Arm Control ==============

@bp.route('/arm_position')
def get_arm_position():
    """Get current arm positions."""
    if not state.arm_connected:
        return jsonify({'error': 'Arm not connected'})
    
    try:
        pos = state.controller.get_arm_position()
        state.update_arm_positions(pos)
        return jsonify({'positions': pos})
    except Exception as e:
        state.last_error = f"Arm read error: {str(e)}"
        return jsonify({'error': str(e)})


@bp.route('/arm', methods=['POST'])
def set_arm():
    """Set arm joint positions."""
    if not state.arm_connected:
        return jsonify({'status': 'error', 'error': 'Arm not connected'})
    
    data = request.json
    positions = data.get('positions', {})
    
    try:
        result = state.controller.set_arm_position(positions)
        state.update_arm_positions(result)
        return jsonify({'status': 'ok', 'positions': result})
    except Exception as e:
        state.last_error = f"Arm write error: {str(e)}"
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/arm/mouse', methods=['POST'])
def arm_mouse():
    """Handle mouse movement for arm control."""
    if not state.arm_connected:
        return jsonify({'status': 'error', 'error': 'Arm not connected'})
    
    data = request.json
    delta_x = float(data.get('deltaX', 0))
    delta_y = float(data.get('deltaY', 0))
    
    try:
        targets = arm_controller.handle_mouse_move(delta_x, delta_y)
        result = state.controller.set_arm_position(targets)
        state.update_arm_positions(result)
        return jsonify({'status': 'ok', 'positions': result})
    except Exception as e:
        state.last_error = f"Arm mouse error: {str(e)}"
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/arm/scroll', methods=['POST'])
def arm_scroll():
    """Handle scroll for wrist roll."""
    if not state.arm_connected:
        return jsonify({'status': 'error', 'error': 'Arm not connected'})
    
    data = request.json
    delta = float(data.get('delta', 0))
    
    try:
        arm_controller.handle_scroll(delta)
        targets = arm_controller.get_targets()
        result = state.controller.set_arm_position(targets)
        state.update_arm_positions(result)
        return jsonify({'status': 'ok', 'wrist_roll': result.get('wrist_roll', 0)})
    except Exception as e:
        state.last_error = f"Arm scroll error: {str(e)}"
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/arm/key', methods=['POST'])
def arm_key():
    """Handle keyboard input for arm control."""
    if not state.arm_connected:
        return jsonify({'status': 'error', 'error': 'Arm not connected'})
    
    data = request.json
    key = data.get('key', '')
    
    try:
        if key == 'q':
            arm_controller.handle_shoulder_pan(-1)
        elif key == 'e':
            arm_controller.handle_shoulder_pan(1)
        elif key == 'r':
            arm_controller.handle_wrist_flex(1)
        elif key == 'f':
            arm_controller.handle_wrist_flex(-1)
        elif key == 't':
            arm_controller.handle_elbow_flex(-1)  # T = elbow up/back
        elif key == 'g':
            arm_controller.handle_elbow_flex(1)   # G = elbow down/forward
        
        targets = arm_controller.get_targets()
        result = state.controller.set_arm_position(targets)
        state.update_arm_positions(result)
        return jsonify({'status': 'ok', 'positions': result})
    except Exception as e:
        state.last_error = f"Arm key error: {str(e)}"
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/gripper', methods=['POST'])
def set_gripper():
    """Set gripper state."""
    if not state.arm_connected:
        return jsonify({'status': 'error', 'error': 'Arm not connected'})
    
    data = request.json
    closed = bool(data.get('closed', False))
    
    try:
        arm_controller.set_gripper(closed)
        result = state.controller.set_gripper(closed)
        state.gripper_closed = closed
        return jsonify({'status': 'ok', 'closed': closed, 'angle': result})
    except Exception as e:
        state.last_error = f"Gripper error: {str(e)}"
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/arm/home', methods=['POST'])
def arm_home():
    """Reset arm to home position."""
    if not state.arm_connected:
        return jsonify({'status': 'error', 'error': 'Arm not connected'})
    
    try:
        targets = arm_controller.reset_to_home()
        result = state.controller.set_arm_position(targets)
        state.update_arm_positions(result)
        return jsonify({'status': 'ok', 'positions': result})
    except Exception as e:
        state.last_error = f"Arm home error: {str(e)}"
        return jsonify({'status': 'error', 'error': str(e)})
