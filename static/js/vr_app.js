AFRAME.registerComponent('vr-controller-updater', {
    init: function () {
        this.rightHand = document.querySelector('#rightHand');
        this.leftHand = document.querySelector('#leftHand');
        this.rightInfo = document.querySelector('#rightHandInfo');
        this.leftInfo = document.querySelector('#leftHandInfo');

        this.socket = null;
        this.rightGripDown = false;
        this.rightTriggerDown = false;
        this.leftStick = { x: 0, y: 0 };
        this.lastSend = 0;
        this.sendInterval = 50;

        // VLA Recording State
        this.recordingActive = false;
        this.recordingEpisode = 0;
        this.framesRecorded = 0;

        // Global access for UI
        window.vrApp = this;

        this.connectSocket();
        this.setupEvents();
    },

    toggleRecording: async function () {
        if (this.recordingActive) {
            this.stopRecording();
        } else {
            const name = prompt("Enter dataset name (e.g., 'pick_cup'):", "dataset_" + Date.now());
            if (!name) return;
            const task = prompt("Enter task description:", "pick up the object");

            try {
                const res = await fetch('/api/vla/record/session/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dataset_name: name, task_description: task })
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    this.setRecordingState(true, name);
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (e) {
                alert('Failed to start session');
            }
        }
    },

    stopRecording: async function () {
        await fetch('/api/vla/record/session/stop', { method: 'POST' });
        this.setRecordingState(false);
    },

    setRecordingState: function (active, name) {
        this.recordingActive = active;
        const panel = document.getElementById('recordingPanel');
        const vrUI = document.getElementById('vrRecUI');

        if (active) {
            panel.classList.remove('hidden');
            document.getElementById('recTaskName').textContent = name;
            if (vrUI) vrUI.setAttribute('visible', true);
        } else {
            panel.classList.add('hidden');
            if (vrUI) vrUI.setAttribute('visible', false);
        }
    },


    connectSocket: function () {
        try {
            this.socket = io(window.location.origin, { transports: ['websocket', 'polling'] });

            this.socket.on('connect', () => {
                this.updateStatus('wsStatus', true);
                this.socket.emit('vr_connect');
            });
            this.socket.on('disconnect', () => this.updateStatus('wsStatus', false));
            this.socket.on('connect_error', () => this.updateStatus('wsStatus', false));
        } catch (e) {
            console.error('Socket error:', e);
        }
    },

    updateStatus: function (id, on) {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('connected', on);
    },

    setupEvents: function () {
        if (!this.rightHand || !this.leftHand) return;

        this.rightHand.addEventListener('gripdown', () => {
            this.rightGripDown = true;
            this.updateStatus('armStatus', true);
        });
        this.rightHand.addEventListener('gripup', () => {
            this.rightGripDown = false;
            if (this.socket?.connected) this.socket.emit('vr_data', { gripReleased: true });
            this.updateStatus('armStatus', false);
        });

        this.rightHand.addEventListener('triggerdown', () => this.rightTriggerDown = true);
        this.rightHand.addEventListener('triggerup', () => {
            this.rightTriggerDown = false;
            if (this.socket?.connected) this.socket.emit('vr_data', { triggerReleased: true });
        });

        this.leftHand.addEventListener('thumbstickmoved', e => {
            this.leftStick = { x: e.detail.x, y: e.detail.y };
        });

        // VLA Recording Buttons (A/B)
        // Note: A-Frame maps Oculus 'A' or 'X' to 'abuttondown' depending on hand
        this.rightHand.addEventListener('abuttondown', () => {
            if (this.socket?.connected) {
                this.socket.emit('vr_data', { aButtonPressed: true });
                // Optimistic UI update
                if (this.recordingActive) this.flashRecStatus('Saved');
            }
        });

        this.rightHand.addEventListener('bbuttondown', () => {
            if (this.socket?.connected) {
                this.socket.emit('vr_data', { bButtonPressed: true });
                if (this.recordingActive) this.flashRecStatus('Discarded', 'red');
            }
        });
    },

    flashRecStatus: function (text, color = 'green') {
        const el = document.getElementById('vrRecStatus');
        if (!el) return;
        const original = el.getAttribute('value');
        el.setAttribute('value', text);
        el.setAttribute('color', color);
        setTimeout(() => {
            el.setAttribute('value', 'REC [ ]'); // Reset to default
            el.setAttribute('color', 'red');
        }, 1500);

    },

    tick: function () {
        if (!this.rightHand || !this.socket?.connected) return;

        const now = Date.now();
        if (now - this.lastSend < this.sendInterval) return;
        this.lastSend = now;

        const right = {
            position: null, quaternion: null,
            gripActive: this.rightGripDown,
            trigger: this.rightTriggerDown ? 1 : 0
        };

        if (this.rightHand.object3D.visible) {
            const p = this.rightHand.object3D.position;
            const q = this.rightHand.object3D.quaternion;
            right.position = { x: p.x, y: p.y, z: p.z };
            right.quaternion = { x: q.x, y: q.y, z: q.z, w: q.w };

            if (this.rightInfo) {
                this.rightInfo.setAttribute('value',
                    this.rightGripDown ? 'ACTIVE' : 'Ready'
                );
            }
        }

        if (this.leftInfo) {
            const { x, y } = this.leftStick;
            this.leftInfo.setAttribute('value',
                (Math.abs(x) > 0.1 || Math.abs(y) > 0.1) ? 'Moving' : 'Move'
            );
        }

        const hasInput = right.gripActive || right.trigger > 0 ||
            Math.abs(this.leftStick.x) > 0.1 || Math.abs(this.leftStick.y) > 0.1;

        if (hasInput && right.position) {
            this.socket.emit('vr_data', {
                rightController: right,
                leftController: { thumbstick: this.leftStick }
            });
        }
    }
});

// Global helpers
function toggleRecording() {
    if (window.vrApp) window.vrApp.toggleRecording();
}
function stopRecordingSession() {
    if (window.vrApp) window.vrApp.stopRecording();
}

