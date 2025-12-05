"""
RoboCrew Control System - Flask Routes
Blueprint containing all HTTP endpoints.
"""

from flask import Blueprint, Response, jsonify, request, render_template

from state import state
from camera import generate_frames
from movement import execute_movement

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
        'head_yaw': state.head_yaw,
        'head_pitch': state.head_pitch,
        'movement': state.movement,
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


# ==================== ARM CONTROL ENDPOINTS ====================

@bp.route('/arm_position')
def get_arm_position():
    """Get current arm joint positions."""
    if state.controller is None:
        return jsonify({'error': 'No controller connected'})
    
    try:
        positions = state.controller.get_arm_position()
        return jsonify({'status': 'ok', 'positions': positions})
    except Exception as e:
        state.last_error = f"Arm read error: {str(e)}"
        print(f"[ARM READ ERROR] {e}")
        return jsonify({'error': str(e)})


@bp.route('/arm_joint', methods=['POST'])
def set_arm_joint():
    """Set a single arm joint position."""
    if state.controller is None:
        return jsonify({'status': 'error', 'error': 'No controller connected'})
    
    data = request.json
    joint = data.get('joint')
    degrees = float(data.get('degrees', 0))
    
    if not joint:
        return jsonify({'status': 'error', 'error': 'No joint specified'})
    
    try:
        result = state.controller.set_arm_joint(joint, degrees)
        return jsonify({'status': 'ok', 'joint': joint, 'degrees': result.get(joint, degrees)})
    except ValueError as e:
        return jsonify({'status': 'error', 'error': str(e)})
    except Exception as e:
        state.last_error = f"Arm write error: {str(e)}"
        print(f"[ARM WRITE ERROR] {e}")
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/arm', methods=['POST'])
def set_arm():
    """Set multiple arm joint positions at once."""
    if state.controller is None:
        return jsonify({'status': 'error', 'error': 'No controller connected'})
    
    data = request.json
    positions = data.get('positions', {})
    
    try:
        result = state.controller.set_arm_position(positions)
        return jsonify({'status': 'ok', 'positions': result})
    except Exception as e:
        state.last_error = f"Arm write error: {str(e)}"
        print(f"[ARM WRITE ERROR] {e}")
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/gripper', methods=['POST'])
def set_gripper():
    """Control the gripper (open/close)."""
    if state.controller is None:
        return jsonify({'status': 'error', 'error': 'No controller connected'})
    
    data = request.json
    open_percent = float(data.get('open', 50))  # Default to half open
    
    try:
        result = state.controller.set_gripper(open_percent)
        return jsonify({'status': 'ok', 'gripper': result.get('gripper', open_percent)})
    except Exception as e:
        state.last_error = f"Gripper error: {str(e)}"
        print(f"[GRIPPER ERROR] {e}")
        return jsonify({'status': 'error', 'error': str(e)})
