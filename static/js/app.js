/**
 * RoboCrew Control - Client-side JavaScript
 */

// DOM Elements
const videoContainer = document.getElementById('video-container');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const connectionDot = document.getElementById('connection-dot');
const debugPanel = document.getElementById('debug-panel');
const compassArrow = document.getElementById('compass-arrow');
const modeIndicator = document.getElementById('mode-indicator');
const modeIcon = document.getElementById('mode-icon');
const modeLabel = document.getElementById('mode-label');
const armPanel = document.getElementById('arm-panel');

// State
let mouseLocked = false;
let currentYaw = null;
let currentPitch = null;
let keysPressed = { w: false, a: false, s: false, d: false };
let lastHeadUpdate = 0;
let headUpdatePending = false;
let controllerConnected = false;
let initialized = false;
let baselineYaw = 0;

// Arm control state
let armMode = false;
let armPositions = {
    shoulder_pan: 0,
    shoulder_lift: 0,
    elbow_flex: 0,
    wrist_flex: 0,
    wrist_roll: 0,
    gripper: 50
};
let lastArmUpdate = 0;
let armUpdatePending = false;
let rightMouseDown = false;
let gripperOpen = true;

// Settings
const MOUSE_SENS = 0.15;
const ARM_SENS = 0.3;
const YAW_MIN = -180, YAW_MAX = 180;
const PITCH_MIN = -180, PITCH_MAX = 180;
const HEAD_UPDATE_INTERVAL = 33;
const ARM_UPDATE_INTERVAL = 50;

function showDebug(msg) {
    debugPanel.textContent = msg;
    debugPanel.classList.add('show');
    console.log('[DEBUG]', msg);
}

function hideDebug() {
    debugPanel.classList.remove('show');
}

function updateCompass() {
    if (currentYaw === null) return;
    const relativeYaw = currentYaw - baselineYaw;
    compassArrow.style.transform = `translate(-50%, -100%) rotate(${-relativeYaw}deg)`;
}

function updateStatus(text, state) {
    statusText.textContent = text;
    statusDot.className = 'status-dot' + (state ? ' ' + state : '');
}

function updateModeIndicator() {
    if (armMode) {
        modeIndicator.classList.add('arm-mode');
        modeIcon.textContent = '🦾';
        modeLabel.textContent = 'Arm';
        videoContainer.classList.add('arm-mode');
        armPanel.classList.add('visible');
        updateStatus('Arm Control', 'arm');
    } else {
        modeIndicator.classList.remove('arm-mode');
        modeIcon.textContent = '🚗';
        modeLabel.textContent = 'Movement';
        videoContainer.classList.remove('arm-mode');
        armPanel.classList.remove('visible');
        if (mouseLocked) {
            updateStatus('Controlling', 'active');
        } else {
            updateStatus('Ready', 'active');
        }
    }
}

function updateArmDisplay() {
    for (const [joint, value] of Object.entries(armPositions)) {
        const el = document.getElementById(`joint-${joint}`);
        if (el) {
            if (joint === 'gripper') {
                el.textContent = `${Math.round(value)}%`;
            } else {
                el.textContent = `${value.toFixed(1)}°`;
            }
        }
    }
}

// Initialize
async function init() {
    updateStatus('Connecting...', '');

    try {
        const res = await fetch('/head_position');
        const data = await res.json();

        if (data.error) {
            showDebug('Head position error: ' + data.error);
            connectionDot.classList.add('error');
            updateStatus('Error', 'error');
            return;
        }

        currentYaw = data.yaw;
        currentPitch = data.pitch;
        baselineYaw = data.yaw;
        controllerConnected = true;
        initialized = true;

        updateCompass();
        connectionDot.classList.remove('error');
        updateStatus('Ready', 'active');

        console.log('Initialized with robot position:', currentYaw, currentPitch);

        // Try to get arm position
        try {
            const armRes = await fetch('/arm_position');
            const armData = await armRes.json();
            if (armData.positions) {
                armPositions = { ...armPositions, ...armData.positions };
                updateArmDisplay();
                console.log('Arm positions:', armPositions);
            }
        } catch (e) {
            console.log('Could not read arm position:', e.message);
        }

    } catch (e) {
        showDebug('Connection error: ' + e.message);
        connectionDot.classList.add('error');
        updateStatus('Offline', 'error');
    }
}

init();

// Pointer Lock
videoContainer.addEventListener('click', () => {
    if (!mouseLocked && initialized) {
        videoContainer.requestPointerLock();
    }
});

document.addEventListener('pointerlockchange', () => {
    mouseLocked = document.pointerLockElement === videoContainer;
    videoContainer.classList.toggle('locked', mouseLocked);
    updateModeIndicator();
});

// Head position updates
let headAbortController = null;

function scheduleHeadUpdate() {
    if (!initialized || armMode) return;

    const now = Date.now();
    const timeSinceLastUpdate = now - lastHeadUpdate;

    if (timeSinceLastUpdate >= HEAD_UPDATE_INTERVAL) {
        sendHeadUpdate();
    } else if (!headUpdatePending) {
        headUpdatePending = true;
        setTimeout(() => {
            headUpdatePending = false;
            sendHeadUpdate();
        }, HEAD_UPDATE_INTERVAL - timeSinceLastUpdate);
    }
}

async function sendHeadUpdate() {
    if (currentYaw === null || currentPitch === null) return;

    if (headAbortController) {
        headAbortController.abort();
    }
    headAbortController = new AbortController();

    lastHeadUpdate = Date.now();
    try {
        await fetch('/head', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ yaw: currentYaw, pitch: currentPitch }),
            signal: headAbortController.signal
        });
    } catch (e) {
        if (e.name !== 'AbortError') {
            console.log('Head update error:', e.message);
        }
    }
}

// Arm position updates
let armAbortController = null;

function scheduleArmUpdate() {
    if (!initialized || !armMode) return;

    const now = Date.now();
    const timeSinceLastUpdate = now - lastArmUpdate;

    if (timeSinceLastUpdate >= ARM_UPDATE_INTERVAL) {
        sendArmUpdate();
    } else if (!armUpdatePending) {
        armUpdatePending = true;
        setTimeout(() => {
            armUpdatePending = false;
            sendArmUpdate();
        }, ARM_UPDATE_INTERVAL - timeSinceLastUpdate);
    }
}

async function sendArmUpdate() {
    if (armAbortController) {
        armAbortController.abort();
    }
    armAbortController = new AbortController();

    lastArmUpdate = Date.now();
    try {
        await fetch('/arm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ positions: armPositions }),
            signal: armAbortController.signal
        });
    } catch (e) {
        if (e.name !== 'AbortError') {
            console.log('Arm update error:', e.message);
        }
    }
}

// Clamp helper
function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

// Mouse movement
document.addEventListener('mousemove', (e) => {
    if (!mouseLocked || !initialized) return;

    if (armMode) {
        // Arm control mode
        if (rightMouseDown) {
            // Right-click + drag: wrist control
            armPositions.wrist_roll = clamp(armPositions.wrist_roll + e.movementX * ARM_SENS, -180, 180);
            armPositions.wrist_flex = clamp(armPositions.wrist_flex + e.movementY * ARM_SENS, -90, 90);
        } else {
            // Normal mouse: shoulder control
            armPositions.shoulder_pan = clamp(armPositions.shoulder_pan + e.movementX * ARM_SENS, -90, 90);
            armPositions.shoulder_lift = clamp(armPositions.shoulder_lift + e.movementY * ARM_SENS, -90, 90);
        }
        updateArmDisplay();
        scheduleArmUpdate();
    } else {
        // Head control mode
        const deltaYaw = e.movementX * MOUSE_SENS;
        const deltaPitch = e.movementY * MOUSE_SENS;

        currentYaw = Math.max(YAW_MIN, Math.min(YAW_MAX, currentYaw + deltaYaw));
        currentPitch = Math.max(PITCH_MIN, Math.min(PITCH_MAX, currentPitch + deltaPitch));

        updateCompass();
        scheduleHeadUpdate();
    }
});

// Scroll wheel for elbow
document.addEventListener('wheel', (e) => {
    if (!mouseLocked || !initialized || !armMode) return;

    e.preventDefault();
    const delta = e.deltaY > 0 ? -2 : 2;
    armPositions.elbow_flex = clamp(armPositions.elbow_flex + delta, -90, 90);
    updateArmDisplay();
    scheduleArmUpdate();
}, { passive: false });

// Right mouse button for wrist
document.addEventListener('mousedown', (e) => {
    if (e.button === 2 && mouseLocked && armMode) {
        rightMouseDown = true;
    }
});

document.addEventListener('mouseup', (e) => {
    if (e.button === 2) {
        rightMouseDown = false;
    }
});

// Prevent context menu
document.addEventListener('contextmenu', (e) => {
    if (mouseLocked) {
        e.preventDefault();
    }
});

// Keyboard controls
async function sendMovement() {
    if (armMode) return; // No movement in arm mode

    const isMoving = Object.values(keysPressed).some(v => v);

    if (isMoving) {
        updateStatus('Moving', 'moving');
    } else if (mouseLocked) {
        updateStatus('Controlling', 'active');
    } else {
        updateStatus('Ready', 'active');
    }

    try {
        const res = await fetch('/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                forward: keysPressed.w,
                backward: keysPressed.s,
                left: keysPressed.a,
                right: keysPressed.d
            })
        });
        const data = await res.json();
        if (data.status === 'error') {
            showDebug('Move error: ' + data.error);
            updateStatus('Error', 'error');
        }
    } catch (e) {
        showDebug('Move request failed: ' + e.message);
    }
}

async function toggleGripper() {
    gripperOpen = !gripperOpen;
    armPositions.gripper = gripperOpen ? 100 : 0;
    updateArmDisplay();

    try {
        await fetch('/gripper', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ open: armPositions.gripper })
        });
    } catch (e) {
        console.log('Gripper error:', e.message);
    }
}

document.addEventListener('keydown', (e) => {
    if (!initialized) return;

    const key = e.key.toLowerCase();

    // Tab to toggle mode
    if (e.key === 'Tab') {
        e.preventDefault();
        armMode = !armMode;
        updateModeIndicator();

        // Stop movement when switching to arm mode
        if (armMode) {
            keysPressed = { w: false, a: false, s: false, d: false };
            sendMovement();
        }
        return;
    }

    // Space for gripper (only in arm mode)
    if (e.key === ' ' && armMode && mouseLocked) {
        e.preventDefault();
        toggleGripper();
        return;
    }

    // WASD (only in movement mode)
    if (!armMode && ['w', 'a', 's', 'd'].includes(key) && !keysPressed[key]) {
        keysPressed[key] = true;
        sendMovement();
    }
});

document.addEventListener('keyup', (e) => {
    const key = e.key.toLowerCase();
    if (['w', 'a', 's', 'd'].includes(key)) {
        keysPressed[key] = false;
        if (!armMode) {
            sendMovement();
        }
    }
});

// Stop movement on window blur
window.addEventListener('blur', () => {
    keysPressed = { w: false, a: false, s: false, d: false };
    if (!armMode) {
        sendMovement();
    }
});
