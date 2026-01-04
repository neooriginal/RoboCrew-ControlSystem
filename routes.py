
"""RoboCrew Flask Routes"""

import cv2
import time
import numpy as np
from flask import Blueprint, Response, jsonify, request, render_template

from state import state
from camera import generate_frames, generate_frames_right
from movement import execute_movement
from arm import arm_controller
import tts
from core.memory_store import memory_store

bp = Blueprint('robot', __name__)


@bp.route('/')
def index():
    return render_template('dashboard.html')

@bp.route('/remote')
def remote():
    return render_template('remote.html')

@bp.route('/status')
def get_status():
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
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@bp.route('/video_feed_right')
def video_feed_right():
    return Response(generate_frames_right(), mimetype='multipart/x-mixed-replace; boundary=frame')


@bp.route('/head_position')
def get_head_position():
    if state.controller is None:
        return jsonify({'error': 'No controller'})
    
    try:
        pos = state.controller.get_head_position()
        yaw = round(pos.get(7, 0), 1)
        pitch = round(pos.get(8, 0), 1)
        state.head_yaw = yaw
        state.head_pitch = pitch
        return jsonify({'yaw': yaw, 'pitch': pitch})
    except Exception as e:
        state.last_error = str(e)
        return jsonify({'error': str(e)})


@bp.route('/head', methods=['POST'])
def set_head():
    if state.controller is None:
        return jsonify({'status': 'error', 'error': 'No controller'})
    
    data = request.json
    yaw = float(data.get('yaw', state.head_yaw))
    pitch = float(data.get('pitch', state.head_pitch))
    
    try:
        # Controller clamps values to safe limits and returns actual position
        yaw_result = state.controller.turn_head_yaw(yaw)
        pitch_result = state.controller.turn_head_pitch(pitch)
        # Use the actual clamped values
        actual_yaw = list(yaw_result.values())[0] if yaw_result else yaw
        actual_pitch = list(pitch_result.values())[0] if pitch_result else pitch
        state.head_yaw = actual_yaw
        state.head_pitch = actual_pitch
        state.last_remote_activity = time.time()
        return jsonify({'status': 'ok', 'yaw': actual_yaw, 'pitch': actual_pitch})
    except Exception as e:
        state.last_error = str(e)
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/move', methods=['POST'])
def move():
    if state.controller is None:
        return jsonify({'status': 'error', 'error': 'No controller'})
    
    data = request.json
    state.update_movement(data)
    
    movement = state.get_movement()
    success = execute_movement(movement)
    
    if any(movement.values()):
        state.last_remote_activity = time.time()
        state.last_movement_activity = time.time()

    
    return jsonify({'status': 'ok' if success else 'error'})


# Mode routes

@bp.route('/mode', methods=['GET'])
def get_mode():
    return jsonify({'mode': state.get_control_mode()})


@bp.route('/mode', methods=['POST'])
def set_mode():
    data = request.json
    mode = data.get('mode', 'drive')
    
    if state.set_control_mode(mode):
        return jsonify({'status': 'ok', 'mode': mode})
    return jsonify({'status': 'error', 'error': f'Invalid mode: {mode}'})


# Arm routes

@bp.route('/arm_position')
def get_arm_position():
    if not state.arm_connected:
        return jsonify({'error': 'Arm not connected'})
    
    try:
        pos = state.controller.get_arm_position()
        state.update_arm_positions(pos)
        return jsonify({'positions': pos})
    except Exception as e:
        return jsonify({'error': str(e)})


@bp.route('/arm', methods=['POST'])
def set_arm():
    if not state.arm_connected:
        return jsonify({'status': 'error', 'error': 'Arm not connected'})
    
    data = request.json
    positions = data.get('positions', {})
    
    try:
        result = state.controller.set_arm_position(positions)
        state.update_arm_positions(result)
        return jsonify({'status': 'ok', 'positions': result})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/arm/mouse', methods=['POST'])
def arm_mouse():
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
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/arm/scroll', methods=['POST'])
def arm_scroll():
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
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/arm/key', methods=['POST'])
def arm_key():
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
            arm_controller.handle_elbow_flex(-1)
        elif key == 'g':
            arm_controller.handle_elbow_flex(1)
        
        targets = arm_controller.get_targets()
        result = state.controller.set_arm_position(targets)
        state.update_arm_positions(result)
        return jsonify({'status': 'ok', 'positions': result})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/gripper', methods=['POST'])
def set_gripper():
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
        return jsonify({'status': 'error', 'error': str(e)})


@bp.route('/arm/home', methods=['POST'])
def arm_home():
    if not state.arm_connected:
        return jsonify({'status': 'error', 'error': 'Arm not connected'})
    
    try:
        targets = arm_controller.reset_to_home()
        result = state.controller.set_arm_position(targets)
        state.update_arm_positions(result)
        return jsonify({'status': 'ok', 'positions': result})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})


# AI Routes

@bp.route('/ai/start', methods=['POST'])
def ai_start():
    if not state.agent:
        return jsonify({'status': 'error', 'error': 'AI Agent not initialized'})
    
    # Save current task if set (so we don't wipe it on start)
    current_task = None
    if hasattr(state.agent, 'current_task'):
        current_task = state.agent.current_task

    # Clear previous context
    state.agent.reset()
    
    # Restore task
    if current_task:
        state.agent.set_task(current_task)
    
    # Reset wheel speed to default when AI starts
    state.reset_wheel_speed()
    
    state.ai_enabled = True
    state.add_ai_log("AI Started")
    return jsonify({'status': 'ok'})

@bp.route('/ai/stop', methods=['POST'])
def ai_stop():
    state.ai_enabled = False
    state.precision_mode = False
    
    # Clear context on stop as well
    if state.agent:
        state.agent.reset()
        
    state.add_ai_log("AI Stopped")
    return jsonify({'status': 'ok'})

@bp.route('/ai/task', methods=['POST'])
def ai_task():
    if not state.agent:
        return jsonify({'status': 'error', 'error': 'AI Agent not initialized'})
    data = request.json
    task = data.get('task', '')
    if task:
        state.agent.set_task(task)
        state.add_ai_log(f"New Task: {task}")
    return jsonify({'status': 'ok'})

@bp.route('/ai/status')
def ai_status():
    return jsonify({
        'enabled': state.ai_enabled,
        'status': state.ai_status,
        'logs': state.ai_logs
    })

@bp.route('/emergency_stop', methods=['POST'])
def emergency_stop():
    state.ai_enabled = False
    state.precision_mode = False
    state.stop_all_movement()
    if state.robot_system:
        state.robot_system.emergency_stop()
    state.add_ai_log("EMERGENCY STOP TRIGGERED")
    return jsonify({'status': 'ok'})

@bp.route('/ai')
def ai_page():
    return render_template('ai_control.html')


# TTS Routes

@bp.route('/tts/speak', methods=['POST'])
def tts_speak():
    data = request.json
    text = data.get('text', '')
    if text:
        tts.speak(text)
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'error': 'No text provided'}), 400


# Wheel Speed Routes

@bp.route('/wheels/speed', methods=['POST'])
def set_wheel_speed():
    data = request.json
    speed = data.get('speed', 10000)
    try:
        state.set_wheel_speed(speed)
        return jsonify({'status': 'ok', 'speed': state.get_wheel_speed()})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 400

@bp.route('/wheels/speed', methods=['GET'])
def get_wheel_speed():
    return jsonify({'speed': state.get_wheel_speed()})


@bp.route('/display')
def display_page():
    """Serve the fullscreen display visualization page."""
    return render_template('display.html')


@bp.route('/display/state')
def display_state():
    """API endpoint for display to poll current robot state."""
    # Determine control mode: remote, ai, or idle
    is_remote = (time.time() - state.last_remote_activity) < 3  # Active within 3 seconds
    if state.ai_enabled:
        control_mode = 'ai'
    elif is_remote:
        control_mode = 'remote'
    else:
        control_mode = 'idle'
    
    return jsonify({
        'ai_enabled': state.ai_enabled,
        'ai_status': state.ai_status,
        'current_task': state.agent.current_task if state.agent and hasattr(state.agent, 'current_task') else None,
        'controller_connected': state.controller is not None,
        'camera_connected': state.camera is not None and state.camera.isOpened() if state.camera else False,
        'arm_connected': state.arm_connected,
        'control_mode': control_mode,
        'precision_mode': state.precision_mode,
        'blockage': state.get_detector().latest_blockage if state.detector else {}
    })


def generate_cv_frames():
    """Generate CV-processed frames showing what the AI sees with Obstacle Detection."""
    import time
    # Initialize detector (Shared)
    detector = state.get_detector()
    
    while state.running:
        if state.robot_system is None:
            time.sleep(0.1)
            continue
        
        try:
            # Thread-safe frame capture
            frame = state.robot_system.get_frame()
            if frame is None:
                time.sleep(0.02)
                continue
            
            # Process frame using the new ObstacleDetector
            # Now returns (safe_actions, overlay, metrics)
            safe_actions, overlay, metrics = detector.process(frame)
            
            # Add AI status overlay on top of the detector's overlay
            if state.ai_enabled:
                cv2.putText(overlay, "AI: ACTIVE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                cv2.putText(overlay, "AI: PAUSED", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 128, 128), 2)
            
            # Add task
            if state.agent and hasattr(state.agent, 'current_task'):
                task_text = state.agent.current_task[:40] if len(state.agent.current_task) > 40 else state.agent.current_task
                cv2.putText(overlay, task_text, (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Display Safe Actions cleanly
            if "FORWARD" not in safe_actions:
                 cv2.putText(overlay, "BLOCKED AHEAD", (overlay.shape[1]//2 - 80, overlay.shape[0]//2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            _, buffer = cv2.imencode('.jpg', overlay, [cv2.IMWRITE_JPEG_QUALITY, 70])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception as e:
            time.sleep(0.05)


@bp.route('/ai_video_feed')
def ai_video_feed():
    return Response(generate_cv_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@bp.route('/memory')
def memory_page():
    return render_template('memory.html')


@bp.route('/api/memory', methods=['GET'])
def get_memories():
    notes = memory_store.get_notes(limit=50)
    return jsonify({'notes': notes})


@bp.route('/api/memory', methods=['POST'])
def add_memory():
    data = request.json
    category = data.get('category', 'other')
    content = data.get('content', '')
    if not content:
        return jsonify({'status': 'error', 'error': 'Content required'}), 400
    note_id = memory_store.save_note(category, content)
    return jsonify({'status': 'ok', 'id': note_id})


@bp.route('/api/memory/<int:note_id>', methods=['DELETE'])
def delete_memory(note_id):
    with memory_store._db_lock:
        cursor = memory_store.conn.cursor()
        cursor.execute('DELETE FROM notes WHERE id = ?', (note_id,))
        memory_store.conn.commit()
        deleted = cursor.rowcount > 0
    if deleted:
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'error': 'Note not found'}), 404


@bp.route('/api/memory/<int:note_id>', methods=['PUT'])
def update_memory(note_id):
    from core.memory_store import memory_store
    data = request.json
    category = data.get('category')
    content = data.get('content')
    
    with memory_store._db_lock:
        cursor = memory_store.conn.cursor()
        if category and content:
            cursor.execute('UPDATE notes SET category = ?, content = ? WHERE id = ?', (category, content, note_id))
        elif content:
            cursor.execute('UPDATE notes SET content = ? WHERE id = ?', (content, note_id))
        elif category:
            cursor.execute('UPDATE notes SET category = ? WHERE id = ?', (category, note_id))
        memory_store.conn.commit()
        updated = cursor.rowcount > 0
    
    if updated:
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'error': 'Note not found'}), 404


@bp.route('/api/memory/clear', methods=['POST'])
def clear_memories():
    memory_store.clear_all()
    return jsonify({'status': 'ok'})





# VR Control Routes

@bp.route('/vr')
def vr_page():
    """VR control page for Quest 3."""
    return render_template('vr_control.html')


@bp.route('/api/vr/status')
def vr_status():
    """Get VR server status."""
    from vr_arm_controller import vr_arm_controller
    
    connected = False
    arm_mode = 'idle'
    
    if vr_arm_controller:
        if vr_arm_controller.vr_server:
            connected = vr_arm_controller.vr_server.is_running
        arm_mode = vr_arm_controller.mode.value if vr_arm_controller.mode else 'idle'
    
    return jsonify({
        'server_running': connected,
        'arm_mode': arm_mode,
        'arm_connected': state.arm_connected
    })


# VLA Routes

@bp.route('/vla')
def vla_page():
    return render_template('vla.html')

@bp.route('/api/vla/status')
def vla_status():
    vla = state.get_vla_system()
    if not vla:
        return jsonify({'error': 'VLA System not available'})
    return jsonify(vla.get_status())

@bp.route('/api/vla/record/start', methods=['POST'])
def vla_record_start():
    vla = state.get_vla_system()
    if not vla:
        return jsonify({'status': 'error', 'error': 'VLA System not available'})
        
    data = request.json
    name = data.get('name')
    success, result = vla.start_recording(name)
    if success:
        return jsonify({'status': 'ok', 'dataset': result})
    return jsonify({'status': 'error', 'error': result})

@bp.route('/api/vla/record/stop', methods=['POST'])
def vla_record_stop():
    vla = state.get_vla_system()
    if not vla:
        return jsonify({'status': 'error', 'error': 'VLA System not available'})
        
    success, count = vla.stop_recording()
    if success:
        return jsonify({'status': 'ok', 'frames': count})
    return jsonify({'status': 'error', 'error': count})

@bp.route('/api/vla/record/discard', methods=['POST'])
def vla_record_discard():
    vla = state.get_vla_system()
    if not vla:
        return jsonify({'status': 'error', 'error': 'VLA System not available'})
        
    success = vla.recorder.discard_current()
    success = vla.recorder.discard_current()
    if success:
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'error': 'Failed to discard'})

@bp.route('/api/vla/record/delete_last', methods=['POST'])
def vla_record_delete_last():
    vla = state.get_vla_system()
    if not vla:
        return jsonify({'status': 'error', 'error': 'VLA System not available'})
        
    success = vla.recorder.delete_last_episode()
    if success:
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'error': 'Failed to delete'})

@bp.route('/api/vla/datasets')
def vla_datasets():
    vla = state.get_vla_system()
    if not vla:
        return jsonify({'datasets': []})
    
    # List directories in dataset root
    root = vla.recorder.dataset_root
    if not root.exists():
        return jsonify({'datasets': []})
        
    datasets = [d.name for d in root.iterdir() if d.is_dir()]
    return jsonify({'datasets': datasets})

@bp.route('/api/vla/dataset/delete', methods=['POST'])
def vla_delete_dataset():
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify({"error": "Missing dataset name"}), 400
        
    dataset_path = state.vla_system.recorder.dataset_root / name
    if not dataset_path.exists():
        return jsonify({"error": "Dataset not found"}), 404
        
    try:
        import shutil
        shutil.rmtree(dataset_path)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/api/vla/dataset/upload_hub', methods=['POST'])
def vla_upload_dataset_hub():
    """Upload a local dataset to Hugging Face Hub."""
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify({"error": "Missing dataset name"}), 400
        
    try:
        from huggingface_hub import whoami
        try:
            user_info = whoami()
            username = user_info['name']
        except:
            return jsonify({"error": "Not logged in to Hugging Face"}), 401

        # Use the helper script logic or direct import
        try:
            try:
                from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
            except ImportError:
                from lerobot.datasets.lerobot_dataset import LeRobotDataset
        except ImportError:
             return jsonify({"error": "LeRobot not found"}), 500
            
        # FIXED: Use absolute path for root to ensure LeRobot finds it locally
        dataset_root = state.vla_system.recorder.dataset_root.resolve()
        
        # Try loading (try local/Name first as per format)
        ds = None
        try:
            ds = LeRobotDataset(f"local/{name}", root=dataset_root)
        except:
            try:
                ds = LeRobotDataset(name, root=dataset_root)
            except Exception as e:
                return jsonify({"error": f"Could not load dataset locally: {str(e)}"}), 404
                
        target_repo = f"{username}/{name}"
        ds.push_to_hub(target_repo, private=True)
        
        return jsonify({"status": "ok", "repo_id": target_repo})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/api/vla/model/delete', methods=['POST'])
def vla_delete_model():
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify({"error": "Missing model name"}), 400
        
    model_path = state.vla_system.executor.models_dir / f"{name}.pth"
    if not model_path.exists():
        return jsonify({"error": "Model not found"}), 404
        
    try:
        model_path.unlink()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/api/vla/models')
def vla_models():
    """List trained LeRobot models."""
    vla = state.get_vla_system()
    if not vla:
        return jsonify({'models': []})
    
    # List LeRobot model directories
    models = vla.list_models()
    model_names = [m.get('name', '') for m in models if m]
    return jsonify({'models': model_names})

@bp.route('/api/vla/execute/start', methods=['POST'])
def vla_execute_start():
    vla = state.get_vla_system()
    if not vla:
        return jsonify({'status': 'error', 'error': 'VLA System not available'})
        
    data = request.json
    model = data.get('model')
    
    if not model:
        return jsonify({'status': 'error', 'error': 'Missing model name'})
        
    success, msg = vla.start_execution(model)
    if success:
        return jsonify({'status': 'ok', 'message': msg})
    return jsonify({'status': 'error', 'error': msg})

@bp.route('/api/vla/execute/stop', methods=['POST'])
def vla_execute_stop():
    vla = state.get_vla_system()
    if not vla:
        return jsonify({'status': 'error', 'error': 'VLA System not available'})
    vla.stop_execution()
    return jsonify({'status': 'ok'})


# ── Training Routes ──

@bp.route('/api/vla/train/start', methods=['POST'])
def vla_train_start():
    """Start training an ACT policy."""
    vla = state.get_vla_system()
    if not vla:
        return jsonify({'status': 'error', 'error': 'VLA System not available'})
        
    data = request.json
    dataset_name = data.get('dataset')
    model_name = data.get('model_name', 'act_policy')
    epochs = data.get('epochs', 100)
    
    if not dataset_name:
        return jsonify({'status': 'error', 'error': 'Missing dataset name'})
        
    success, msg = vla.start_training(dataset_name, model_name, epochs)
    if success:
        return jsonify({'status': 'ok', 'message': msg})
    return jsonify({'status': 'error', 'error': msg})


@bp.route('/api/vla/train/stop', methods=['POST'])
def vla_train_stop():
    """Stop ongoing training."""
    vla = state.get_vla_system()
    if not vla:
        return jsonify({'status': 'error', 'error': 'VLA System not available'})
        
    success, msg = vla.stop_training()
    if success:
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'error': msg})


@bp.route('/api/vla/train/status')
def vla_train_status():
    """Get training status."""
    vla = state.get_vla_system()
    if not vla:
        return jsonify({'training': False, 'progress': 0, 'status': 'System unavailable'})
    return jsonify(vla.get_training_status())

@bp.route('/api/vla/login', methods=['POST'])
def vla_login():
    """Login to Hugging Face Hub."""
    from flask import request
    data = request.json
    token = data.get('token')
    
    if not token:
        return jsonify({'error': 'Token required'}), 400
        
    try:
        from huggingface_hub import login
        login(token=token)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/vla/login/status')
def vla_login_status():
    """Check Hugging Face login status."""
    try:
        from huggingface_hub import whoami
        user = whoami()
        return jsonify({'logged_in': True, 'user': user['name']})
    except:
        return jsonify({'logged_in': False})
