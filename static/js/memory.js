async function loadNotes() {
    try {
        const response = await fetch('/api/memory');
        const data = await response.json();

        const list = document.getElementById('memory-list');
        const stats = document.getElementById('stats');

        if (!data.notes || data.notes.length === 0) {
            list.innerHTML = '<div class="empty-state">No memories yet. The AI will save notes as it explores.</div>';
            stats.textContent = '0 notes';
            return;
        }

        stats.textContent = `${data.notes.length} note${data.notes.length !== 1 ? 's' : ''}`;

        list.innerHTML = data.notes.map(note => `
            <div class="memory-item" data-id="${note.id}">
                <span class="category-badge ${note.category}">${note.category}</span>
                <div class="memory-content" id="content-${note.id}">${escapeHtml(note.content)}</div>
                <div class="memory-actions">
                    <button class="btn-icon edit-btn" data-id="${note.id}" title="Edit">✏️</button>
                    <button class="btn-icon delete-btn" data-id="${note.id}" title="Delete">🗑️</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load notes:', error);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function addNote() {
    const category = document.getElementById('new-category').value;
    const contentInput = document.getElementById('new-content');
    const content = contentInput.value.trim();

    if (!content) return;

    try {
        await fetch('/api/memory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, content })
        });
        contentInput.value = '';
        loadNotes();
    } catch (error) {
        console.error('Failed to add note:', error);
    }
}

async function deleteNote(id) {
    if (!confirm('Delete this note?')) return;
    try {
        await fetch(`/api/memory/${id}`, { method: 'DELETE' });
        loadNotes();
    } catch (error) {
        console.error('Failed to delete note:', error);
    }
}

function editNote(id) {
    const el = document.getElementById(`content-${id}`);
    const currentText = el.textContent;

    el.classList.add('editing');
    el.innerHTML = `
        <input type="text" value="${escapeHtml(currentText)}" id="edit-input-${id}">
        <button class="btn-icon save-btn" data-id="${id}">✓</button>
        <button class="btn-icon cancel-btn">✕</button>
    `;

    document.getElementById(`edit-input-${id}`).focus();
}

async function saveNote(id) {
    const content = document.getElementById(`edit-input-${id}`).value.trim();
    if (!content) return;

    try {
        await fetch(`/api/memory/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });
        loadNotes();
    } catch (error) {
        console.error('Failed to save note:', error);
    }
}

async function clearAll() {
    if (!confirm('Delete ALL memories? This cannot be undone.')) return;

    try {
        await fetch('/api/memory/clear', { method: 'POST' });
        loadNotes();
    } catch (error) {
        console.error('Failed to clear memories:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Static event listeners
    const addBtn = document.getElementById('add-note-btn');
    if (addBtn) addBtn.addEventListener('click', addNote);

    const clearBtn = document.getElementById('clear-all-btn');
    if (clearBtn) clearBtn.addEventListener('click', clearAll);

    const newContentInput = document.getElementById('new-content');
    if (newContentInput) {
        newContentInput.addEventListener('keypress', e => {
            if (e.key === 'Enter') addNote();
        });
    }

    // Event delegation for dynamic lists
    const memoryList = document.getElementById('memory-list');
    if (memoryList) {
        memoryList.addEventListener('click', (e) => {
            const target = e.target.closest('button');
            if (!target) return;

            const id = target.dataset.id;

            if (target.classList.contains('edit-btn')) {
                editNote(id);
            } else if (target.classList.contains('delete-btn')) {
                deleteNote(id);
            } else if (target.classList.contains('save-btn')) {
                saveNote(id);
            } else if (target.classList.contains('cancel-btn')) {
                loadNotes(); // Re-render to cancel
            }
        });
    }

    loadNotes();
});
