/**
 * VLA Training Suite - Dashboard Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    loadDatasets();
    setupEventHandlers();
});

function setupEventHandlers() {
    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) refreshBtn.onclick = loadDatasets;
}

async function loadDatasets() {
    const listEl = document.getElementById('datasetList');
    if (!listEl) return;

    listEl.innerHTML = '<div class="list-item">Loading...</div>';

    try {
        const res = await fetch('/api/vla/datasets');
        const data = await res.json();
        const datasets = data.datasets || [];

        listEl.innerHTML = '';
        if (datasets.length === 0) {
            listEl.innerHTML = '<div class="text-muted" style="padding: 20px; text-align: center;">No datasets found. Start recording!</div>';
            return;
        }

        datasets.forEach(ds => {
            const item = document.createElement('div');
            item.className = 'list-item';

            // Format buttons based on state
            const exportBtn = `<button class="btn" onclick="exportDataset('${ds.name}')">⬇️ ZIP</button>`;

            item.innerHTML = `
                <div>
                    <div style="font-weight:600; font-size:1.1rem;">${ds.name}</div>
                    <div style="font-size:0.9rem; color:#888;">${ds.episodes} episodes</div>
                </div>
                <div style="display:flex; gap:10px;">
                    ${exportBtn}
                    <button class="btn btn-danger" onclick="deleteDataset('${ds.name}')">🗑️</button>
                    <button class="btn btn-primary" onclick="startTraining('${ds.name}')">🎯 Train</button>
                </div>
            `;
            listEl.appendChild(item);
        });

    } catch (e) {
        console.error("Failed to load datasets", e);
        listEl.innerHTML = '<div class="error">Error loading datasets</div>';
    }
}

async function deleteDataset(name) {
    if (!confirm(`Are you sure you want to delete dataset '${name}'?`)) return;

    try {
        await fetch(`/api/vla/datasets/${name}`, { method: 'DELETE' });
        loadDatasets();
    } catch (e) {
        alert("Delete failed");
    }
}

async function exportDataset(name) {
    const btn = event.target;
    btn.textContent = "⏳ Zipping...";
    btn.disabled = true;

    try {
        const res = await fetch(`/api/vla/datasets/export/${name}`);
        const data = await res.json();

        if (data.status === 'ok' && data.download_url) {
            // Trigger download
            window.location.href = data.download_url;
            btn.textContent = "✅ Started";
            setTimeout(() => {
                btn.textContent = "⬇️ ZIP";
                btn.disabled = false;
            }, 3000);
        } else {
            alert('Export failed: ' + (data.error || 'Unknown error'));
            btn.textContent = "❌ Error";
        }
    } catch (e) {
        alert('Export request failed');
        btn.textContent = "❌ Error";
    }
}

async function startTraining(datasetName) {
    if (!confirm(`Start training on Pi 4 CPU?\n\nWARNING: This will be extremely slow. It is recommended to download the ZIP and train on a PC.`)) return;

    try {
        const res = await fetch('/api/vla/train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset: datasetName })
        });
        const data = await res.json();
        alert(data.message || data.status);
    } catch (e) {
        alert("Failed to start training");
    }
}

// Global scope for onclick handlers
window.deleteDataset = deleteDataset;
window.exportDataset = exportDataset;
window.startTraining = startTraining;
window.loadDatasets = loadDatasets;
