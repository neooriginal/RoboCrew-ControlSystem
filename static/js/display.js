/**
 * RoboCrew Display Visualization
 * Animated eyes and status display
 */

class RoboDisplay {
    constructor() {
        this.leftIris = document.getElementById('left-iris');
        this.rightIris = document.getElementById('right-iris');
        this.leftEye = document.getElementById('left-eye');
        this.rightEye = document.getElementById('right-eye');
        this.statusDot = document.getElementById('status-dot');
        this.statusLabel = document.getElementById('status-label');
        this.taskDisplay = document.getElementById('task-display');
        this.touchPrompt = document.getElementById('touch-prompt');
        this.connectionBadge = document.getElementById('connection-badge');
        this.container = document.getElementById('display-container');

        this.currentExpression = 'idle';
        this.isBlinking = false;
        this.lookTarget = { x: 0, y: 0 };
        this.currentLook = { x: 0, y: 0 };

        this.init();
    }

    init() {
        // Fullscreen on click/touch
        this.container.addEventListener('click', () => this.toggleFullscreen());
        this.container.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.toggleFullscreen();
        });

        // Start animations
        this.startBlinkLoop();
        this.startLookAroundLoop();
        this.startStatusPolling();
        this.animate();

        // Hide touch prompt after entering fullscreen
        document.addEventListener('fullscreenchange', () => {
            if (document.fullscreenElement) {
                this.touchPrompt.classList.add('hidden');
            }
        });
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            this.container.requestFullscreen().catch(err => {
                console.log('Fullscreen not available:', err);
            });
        } else {
            document.exitFullscreen();
        }
    }

    // Eye movement
    setLookTarget(x, y) {
        // x, y should be in range -1 to 1
        this.lookTarget.x = Math.max(-1, Math.min(1, x));
        this.lookTarget.y = Math.max(-1, Math.min(1, y));
    }

    updateEyePosition() {
        // Smooth interpolation
        this.currentLook.x += (this.lookTarget.x - this.currentLook.x) * 0.1;
        this.currentLook.y += (this.lookTarget.y - this.currentLook.y) * 0.1;

        const maxOffset = 25; // pixels
        const offsetX = this.currentLook.x * maxOffset;
        const offsetY = this.currentLook.y * maxOffset;

        this.leftIris.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
        this.rightIris.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
    }

    // Blinking
    blink() {
        if (this.isBlinking) return;
        this.isBlinking = true;

        this.leftEye.classList.add('blinking');
        this.rightEye.classList.add('blinking');

        setTimeout(() => {
            this.leftEye.classList.remove('blinking');
            this.rightEye.classList.remove('blinking');
            this.isBlinking = false;
        }, 150);
    }

    startBlinkLoop() {
        const doBlink = () => {
            if (this.currentExpression !== 'happy') {
                this.blink();
            }
            // Random interval between 2-6 seconds
            const nextBlink = 2000 + Math.random() * 4000;
            setTimeout(doBlink, nextBlink);
        };
        setTimeout(doBlink, 1000);
    }

    // Look around randomly
    startLookAroundLoop() {
        const lookAround = () => {
            if (this.currentExpression === 'idle' || this.currentExpression === 'active') {
                // Random look direction
                const x = (Math.random() - 0.5) * 1.5;
                const y = (Math.random() - 0.5) * 0.8;
                this.setLookTarget(x, y);
            }
            // Random interval between 1-4 seconds
            const nextLook = 1000 + Math.random() * 3000;
            setTimeout(lookAround, nextLook);
        };
        setTimeout(lookAround, 2000);
    }

    // Expressions
    setExpression(expression) {
        if (this.currentExpression === expression) return;

        // Remove old expression classes
        const expressions = ['happy', 'thinking', 'error'];
        expressions.forEach(exp => {
            this.leftEye.classList.remove(exp);
            this.rightEye.classList.remove(exp);
        });

        // Apply new expression
        if (expressions.includes(expression)) {
            this.leftEye.classList.add(expression);
            this.rightEye.classList.add(expression);
        }

        this.currentExpression = expression;

        // Special behaviors for expressions
        if (expression === 'happy') {
            // Look center when happy
            this.setLookTarget(0, 0);
        } else if (expression === 'thinking') {
            // Look up when thinking
            this.setLookTarget(0.3, -0.5);
        }
    }

    // Status polling
    async startStatusPolling() {
        const poll = async () => {
            try {
                const response = await fetch('/display/state');
                if (response.ok) {
                    const data = await response.json();
                    this.updateFromState(data);
                    this.connectionBadge.classList.remove('disconnected');
                } else {
                    this.connectionBadge.classList.add('disconnected');
                }
            } catch (error) {
                this.connectionBadge.classList.add('disconnected');
            }
            setTimeout(poll, 500);
        };
        poll();
    }

    updateFromState(data) {
        // Update status indicator
        this.statusDot.className = 'status-dot';

        if (data.ai_enabled) {
            this.statusDot.classList.add('active');
            this.statusLabel.textContent = 'AI Active';
            this.setExpression('active');
        } else {
            this.statusDot.classList.add('idle');
            this.statusLabel.textContent = 'Idle';
            this.setExpression('idle');
        }

        // Update task display
        if (data.current_task) {
            this.taskDisplay.textContent = data.current_task;
        } else if (data.ai_status && data.ai_status !== 'Idle') {
            this.taskDisplay.textContent = data.ai_status;
        } else {
            this.taskDisplay.textContent = 'Ready to help!';
        }

        // Expression based on status
        if (data.ai_status) {
            const status = data.ai_status.toLowerCase();
            if (status.includes('error') || status.includes('failed')) {
                this.setExpression('error');
                this.statusDot.className = 'status-dot error';
            } else if (status.includes('thinking') || status.includes('planning')) {
                this.setExpression('thinking');
            } else if (status.includes('complete') || status.includes('success') || status.includes('done')) {
                this.setExpression('happy');
                // Reset to idle after 3 seconds
                setTimeout(() => {
                    if (this.currentExpression === 'happy') {
                        this.setExpression('idle');
                    }
                }, 3000);
            }
        }
    }

    // Animation loop
    animate() {
        this.updateEyePosition();
        requestAnimationFrame(() => this.animate());
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.roboDisplay = new RoboDisplay();
});
