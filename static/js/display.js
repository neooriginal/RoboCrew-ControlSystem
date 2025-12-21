/**
 * RoboCrew Display Visualization - Enhanced Version
 * Animated eyes with particles and dynamic effects
 */

class RoboDisplay {
    constructor() {
        this.leftIris = document.getElementById('left-iris');
        this.rightIris = document.getElementById('right-iris');
        this.leftEye = document.getElementById('left-eye');
        this.rightEye = document.getElementById('right-eye');
        this.eyesContainer = document.getElementById('eyes-container');
        this.statusDot = document.getElementById('status-dot');
        this.statusLabel = document.getElementById('status-label');
        this.taskDisplay = document.getElementById('task-display');
        this.bgParticles = document.getElementById('bg-particles');
        this.bgGlow = document.getElementById('bg-glow');

        // Control mode elements
        this.controlModeBadge = document.getElementById('control-mode-badge');
        this.modeEmoji = document.getElementById('mode-emoji');
        this.modeText = document.getElementById('mode-text');

        // System status elements
        this.systemController = document.getElementById('system-controller');
        this.systemCamera = document.getElementById('system-camera');
        this.systemArm = document.getElementById('system-arm');
        this.systemAI = document.getElementById('system-ai');

        // Blockage zones
        this.warnLeft = document.getElementById('warn-left');
        this.warnCenter = document.getElementById('warn-center');
        this.warnRight = document.getElementById('warn-right');

        this.currentExpression = 'idle';
        this.currentControlMode = 'idle';
        this.isBlinking = false;
        this.lookTarget = { x: 0, y: 0 };
        this.currentLook = { x: 0, y: 0 };

        this.init();
    }

    init() {
        this.createParticles();
        this.startBlinkLoop();
        this.startLookAroundLoop();
        this.startMicroMovements();
        this.startStatusPolling();
        this.animate();
    }

    // Create floating background particles
    createParticles() {
        const colors = [
            'rgba(100, 150, 255, 0.6)',
            'rgba(150, 100, 255, 0.5)',
            'rgba(100, 200, 255, 0.4)',
            'rgba(200, 150, 255, 0.4)'
        ];

        for (let i = 0; i < 20; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDuration = (10 + Math.random() * 15) + 's';
            particle.style.animationDelay = -(Math.random() * 15) + 's';
            particle.style.background = colors[Math.floor(Math.random() * colors.length)];
            particle.style.width = (2 + Math.random() * 4) + 'px';
            particle.style.height = particle.style.width;
            this.bgParticles.appendChild(particle);
        }
    }

    // Eye movement
    setLookTarget(x, y) {
        this.lookTarget.x = Math.max(-1, Math.min(1, x));
        this.lookTarget.y = Math.max(-1, Math.min(1, y));
    }

    updateEyePosition() {
        // Smooth interpolation with slight lag for natural feel
        this.currentLook.x += (this.lookTarget.x - this.currentLook.x) * 0.08;
        this.currentLook.y += (this.lookTarget.y - this.currentLook.y) * 0.08;

        const maxOffset = 28;
        const offsetX = this.currentLook.x * maxOffset;
        const offsetY = this.currentLook.y * maxOffset;

        // Slight parallax - right eye moves slightly more
        this.leftIris.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
        this.rightIris.style.transform = `translate(${offsetX * 1.05}px, ${offsetY}px)`;
    }

    // Blinking with double-blink sometimes
    blink(double = false) {
        if (this.isBlinking) return;
        this.isBlinking = true;

        const doBlink = () => {
            this.leftEye.classList.add('blinking');
            this.rightEye.classList.add('blinking');

            setTimeout(() => {
                this.leftEye.classList.remove('blinking');
                this.rightEye.classList.remove('blinking');
            }, 120);
        };

        doBlink();

        if (double) {
            setTimeout(() => doBlink(), 250);
            setTimeout(() => { this.isBlinking = false; }, 400);
        } else {
            setTimeout(() => { this.isBlinking = false; }, 150);
        }
    }

    startBlinkLoop() {
        const doBlink = () => {
            if (this.currentExpression !== 'happy') {
                // 20% chance of double blink
                this.blink(Math.random() < 0.2);
            }
            // Random interval 2-5 seconds
            const nextBlink = 2000 + Math.random() * 3000;
            setTimeout(doBlink, nextBlink);
        };
        setTimeout(doBlink, 1500);
    }

    // Random micro-movements for liveliness
    startMicroMovements() {
        const microMove = () => {
            if (this.currentExpression === 'idle') {
                // Tiny random adjustments
                const microX = (Math.random() - 0.5) * 0.1;
                const microY = (Math.random() - 0.5) * 0.05;
                this.lookTarget.x += microX;
                this.lookTarget.y += microY;
            }
            setTimeout(microMove, 200 + Math.random() * 300);
        };
        microMove();
    }

    // Look around randomly with varied patterns
    startLookAroundLoop() {
        const lookAround = () => {
            if (this.currentExpression === 'idle' || this.currentExpression === 'active') {
                // Different look patterns
                const pattern = Math.random();
                let x, y;

                if (pattern < 0.3) {
                    // Look at something specific
                    x = (Math.random() - 0.5) * 1.8;
                    y = (Math.random() - 0.5) * 1.0;
                } else if (pattern < 0.5) {
                    // Glance to side
                    x = Math.random() < 0.5 ? -0.8 : 0.8;
                    y = (Math.random() - 0.5) * 0.4;
                } else if (pattern < 0.7) {
                    // Look up thoughtfully
                    x = (Math.random() - 0.5) * 0.4;
                    y = -0.5 - Math.random() * 0.3;
                } else {
                    // Return to center-ish
                    x = (Math.random() - 0.5) * 0.3;
                    y = (Math.random() - 0.5) * 0.2;
                }

                this.setLookTarget(x, y);
            }

            const nextLook = 800 + Math.random() * 2500;
            setTimeout(lookAround, nextLook);
        };
        setTimeout(lookAround, 2000);
    }

    // Expressions with enhanced animations
    setExpression(expression) {
        if (this.currentExpression === expression) return;

        const expressions = ['happy', 'thinking', 'error', 'excited'];
        expressions.forEach(exp => {
            this.leftEye.classList.remove(exp);
            this.rightEye.classList.remove(exp);
        });

        if (expressions.includes(expression)) {
            this.leftEye.classList.add(expression);
            this.rightEye.classList.add(expression);
        }

        this.currentExpression = expression;

        // Special behaviors
        switch (expression) {
            case 'happy':
                this.setLookTarget(0, 0.1);
                // Quick excited look around
                setTimeout(() => {
                    if (this.currentExpression === 'happy') {
                        this.setLookTarget(0.3, 0);
                    }
                }, 500);
                break;
            case 'thinking':
                this.setLookTarget(0.4, -0.6);
                break;
            case 'excited':
                this.blink(true);
                break;
            case 'error':
                // Shake handled by CSS
                break;
        }
    }

    // Control mode update with animation
    updateControlMode(mode, precisionMode = false) {
        // If mode changed OR precision mode toggled while in AI mode
        const isPrecisionChange = (mode === 'ai' && this.lastPrecisionMode !== precisionMode);

        if (this.currentControlMode === mode && !isPrecisionChange) return;

        this.currentControlMode = mode;
        this.lastPrecisionMode = precisionMode;

        this.controlModeBadge.classList.remove('idle', 'remote', 'ai');
        this.controlModeBadge.classList.add(mode);

        // Update emoji and text with bounce effect
        this.modeEmoji.style.transform = 'scale(0.8)';
        setTimeout(() => {
            switch (mode) {
                case 'remote':
                    this.modeEmoji.textContent = '🎮';
                    this.modeText.textContent = 'Remote Control';
                    this.setExpression('active');
                    break;
                case 'ai':
                    this.modeEmoji.textContent = '🤖';
                    if (precisionMode) {
                        this.modeText.textContent = 'AI Precision';
                        this.modeEmoji.textContent = '🎯'; // Target emoji for precision
                    } else {
                        this.modeText.textContent = 'AI Driving';
                    }
                    if (this.currentExpression !== 'thinking' && this.currentExpression !== 'error') {
                        this.setExpression('excited');
                        setTimeout(() => this.setExpression('active'), 1000);
                    }
                    break;
                case 'idle':
                default:
                    this.modeEmoji.textContent = '😴';
                    this.modeText.textContent = 'Idle';
                    break;
            }
            this.modeEmoji.style.transform = 'scale(1.1)';
            setTimeout(() => { this.modeEmoji.style.transform = 'scale(1)'; }, 150);
        }, 100);

        // Update background glow color
        if (mode === 'ai') {
            if (precisionMode) {
                this.bgGlow.style.background = 'radial-gradient(circle, rgba(234, 179, 8, 0.2) 0%, transparent 70%)'; // Yellow for precision
            } else {
                this.bgGlow.style.background = 'radial-gradient(circle, rgba(168, 85, 247, 0.2) 0%, transparent 70%)'; // Purple for normal AI
            }
        } else if (mode === 'remote') {
            this.bgGlow.style.background = 'radial-gradient(circle, rgba(96, 165, 250, 0.2) 0%, transparent 70%)';
        } else {
            this.bgGlow.style.background = 'radial-gradient(circle, rgba(80, 120, 200, 0.15) 0%, transparent 70%)';
        }
    }

    // Update system status indicators
    updateSystemStatus(data) {
        const updateItem = (element, connected) => {
            if (connected) {
                element.classList.add('operational');
                element.classList.remove('offline');
            } else {
                element.classList.add('offline');
                element.classList.remove('operational');
            }
        };

        updateItem(this.systemController, data.controller_connected);
        updateItem(this.systemCamera, data.camera_connected);
        updateItem(this.systemArm, data.arm_connected);
        updateItem(this.systemAI, data.ai_enabled);
    }

    // Status polling
    async startStatusPolling() {
        const poll = async () => {
            try {
                const response = await fetch('/display/state');
                if (response.ok) {
                    const data = await response.json();
                    this.updateFromState(data);
                    this.updateSystemStatus(data);
                    this.updateControlMode(data.control_mode || 'idle', data.precision_mode);
                }
            } catch (error) {
                // Connection lost
                [this.systemController, this.systemCamera, this.systemArm, this.systemAI].forEach(el => {
                    el.classList.add('offline');
                    el.classList.remove('operational');
                });
            }
            setTimeout(poll, 500);
        };
        poll();
    }

    updateFromState(data) {
        this.statusDot.className = 'status-dot';

        if (data.ai_enabled) {
            this.statusDot.classList.add('active');
            this.statusLabel.textContent = 'AI Active';
        } else {
            this.statusDot.classList.add('idle');
            this.statusLabel.textContent = 'Idle';
            if (this.currentControlMode === 'idle') {
                this.setExpression('idle');
            }
        }

        // Update task display
        if (data.current_task) {
            this.taskDisplay.textContent = data.current_task;
        } else if (data.ai_status && data.ai_status !== 'Idle') {
            this.taskDisplay.textContent = data.ai_status;
        } else {
            this.taskDisplay.textContent = 'Ready to help!';
        }

        // Expression based on status keywords
        if (data.ai_status) {
            const status = data.ai_status.toLowerCase();
            if (status.includes('error') || status.includes('failed')) {
                this.setExpression('error');
                this.statusDot.className = 'status-dot error';
            } else if (status.includes('thinking') || status.includes('planning')) {
                this.setExpression('thinking');
            } else if (status.includes('complete') || status.includes('success') || status.includes('done')) {
                this.setExpression('happy');
                setTimeout(() => {
                    if (this.currentExpression === 'happy') {
                        this.setExpression('idle');
                    }
                }, 3000);
            }
        }

        // Update Blockage Visualization
        if (data.blockage) {
            const toggle = (el, active) => {
                if (active) el.classList.add('visible');
                else el.classList.remove('visible');
            };

            toggle(this.warnLeft, data.blockage.left);
            toggle(this.warnCenter, data.blockage.forward);
            toggle(this.warnRight, data.blockage.right);

            // Note: Expression change removed per user request. 
            // The red warning zones are sufficient feedback.
        }
    }

    // Animation loop
    animate() {
        this.updateEyePosition();
        this.updateMap();
        requestAnimationFrame(() => this.animate());
    }

    // Map Visualization
    async updateMap() {
        if (!this.mapCanvas) {
            this.mapCanvas = document.getElementById('slam-map-canvas');
            if (this.mapCanvas) {
                this.mapCtx = this.mapCanvas.getContext('2d');
                // Set resolution
                this.mapCanvas.width = this.mapCanvas.offsetWidth;
                this.mapCanvas.height = this.mapCanvas.offsetHeight;
            } else {
                return;
            }
        }

        // Poll map data every 500ms separately from animation loop
        const now = Date.now();
        if (!this.lastMapPoll || now - this.lastMapPoll > 500) {
            this.lastMapPoll = now;
            try {
                const response = await fetch('/api/map');
                if (response.ok) {
                    this.mapData = await response.json();
                }
            } catch (e) {
                // Ignore errors
            }
        }

        // Render Map
        if (this.mapData && this.mapData.trajectory) {
            this.renderMap(this.mapData);
        }
    }

    renderMap(data) {
        const ctx = this.mapCtx;
        const w = this.mapCanvas.width;
        const h = this.mapCanvas.height;

        // Clear
        ctx.clearRect(0, 0, w, h);

        if (data.trajectory.length === 0) return;

        // Find bounds (X and Z - since Y is usually height in SLAM)
        // Adjust for typical camera coordinates: X=Right, Y=Down, Z=Forward
        // We want Top-Down view: X vs Z.

        let minX = Infinity, maxX = -Infinity;
        let minZ = Infinity, maxZ = -Infinity;

        const POINTS = data.trajectory.concat(data.points || []);

        POINTS.forEach(pt => {
            const x = pt[0];
            const z = pt[2]; // Use Z for depth
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (z < minZ) minZ = z;
            if (z > maxZ) maxZ = z;
        });

        // Add padding
        const padding = 2; // meters
        if (minX === Infinity) { minX = -5; maxX = 5; minZ = -5; maxZ = 5; }

        minX -= padding; maxX += padding;
        minZ -= padding; maxZ += padding;

        const rangeX = maxX - minX;
        const rangeZ = maxZ - minZ;
        const scale = Math.min(w / rangeX, h / rangeZ);

        // Transform helper (World -> Canvas)
        const toCanvas = (x, z) => {
            return {
                x: (x - minX) * scale + (w - rangeX * scale) / 2,
                y: h - ((z - minZ) * scale + (h - rangeZ * scale) / 2) // Invert Y (screen coords)
            };
        };

        // Draw Points (Map)
        ctx.fillStyle = 'rgba(100, 200, 255, 0.5)';
        if (data.points) {
            data.points.forEach(pt => {
                const p = toCanvas(pt[0], pt[2]);
                ctx.beginPath();
                ctx.arc(p.x, p.y, 1, 0, Math.PI * 2);
                ctx.fill();
            });
        }

        // Draw Trajectory
        ctx.strokeStyle = '#4ade80';
        ctx.lineWidth = 2;
        ctx.beginPath();
        data.trajectory.forEach((pt, i) => {
            const p = toCanvas(pt[0], pt[2]);
            if (i === 0) ctx.moveTo(p.x, p.y);
            else ctx.lineTo(p.x, p.y);
        });
        ctx.stroke();

        // Draw Current Pose (Triangle)
        if (data.pose) {
            // Simpler: just last trajectory point
            const last = data.trajectory[data.trajectory.length - 1];
            if (last) {
                const p = toCanvas(last[0], last[2]);
                ctx.fillStyle = '#ff3333';
                ctx.beginPath();
                ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.roboDisplay = new RoboDisplay();
});
