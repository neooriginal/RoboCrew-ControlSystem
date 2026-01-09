
/**
 * Global Log & Notification System
 * Polls /api/logs and handles:
 * 1. Site-wide notifications for errors/warnings.
 * 2. Dispatching 'log-update' event for dashboard console.
 */

class LogManager {
    constructor() {
        this.lastTimestamp = 0;
        this.pollingInterval = 2000; // 2 seconds
        this.isVR = window.location.pathname.includes('/vr');
        this.container = document.getElementById('notification-container');

        // Start polling
        this.poll();
        setInterval(() => this.poll(), this.pollingInterval);
    }

    async poll() {
        try {
            const res = await fetch(`/api/logs?since=${this.lastTimestamp}`);
            const data = await res.json();

            if (data.logs && data.logs.length > 0) {
                this.processLogs(data.logs);

                // Update timestamp to the latest one
                const latest = data.logs[data.logs.length - 1];
                this.lastTimestamp = latest.created;
            }
        } catch (e) {
            console.error("Failed to poll logs", e);
        }
    }

    processLogs(logs) {
        // Dispatch event for other components (like dashboard console)
        const event = new CustomEvent('log-update', { detail: logs });
        document.dispatchEvent(event);

        // Handle Notifications
        if (!this.container) return;

        logs.forEach(log => {
            // Check for critical/error logs
            if (['ERROR', 'CRITICAL'].includes(log.level)) {
                this.showNotification(log);
            }
        });
    }

    showNotification(log) {
        // Skip if VR page (User Request: "not on VR page")
        if (this.isVR) return;

        // Prevent duplicate visible notifications (simple check)
        const existing = Array.from(this.container.children).find(el => el.textContent.includes(log.message));
        if (existing) return;

        // Create Element
        const toast = document.createElement('div');
        toast.className = `notification-toast ${log.level.toLowerCase()}`;

        toast.innerHTML = `
            <div class="toast-icon">⚠️</div>
            <div class="toast-content">
                <div class="toast-title">System Alert</div>
                <div class="toast-message">${this.escapeHtml(log.message)}</div>
            </div>
            <button class="toast-close">&times;</button>
        `;

        // Close button
        toast.querySelector('.toast-close').onclick = () => {
            this.dismiss(toast);
        };

        // Add to container
        this.container.appendChild(toast);

        // Auto remove after 5s
        setTimeout(() => {
            this.dismiss(toast);
        }, 5000);
    }

    dismiss(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateY(10px) scale(0.95)';
        setTimeout(() => {
            if (element.parentElement) element.remove();
        }, 300);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    window.logManager = new LogManager();
});
