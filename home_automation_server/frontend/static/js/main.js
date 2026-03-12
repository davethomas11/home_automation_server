/**
 * Vectrune – Main JS
 * Shared utilities used across all pages.
 */

// Highlight the active nav link
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    document.querySelectorAll('nav a').forEach(a => {
        if (a.getAttribute('href') !== '/docs' && path.startsWith(a.getAttribute('href'))) {
            a.style.color = 'var(--accent-hover)';
            a.style.fontWeight = '600';
        }
    });
});

/**
 * Generic fetch helper with JSON body.
 * @param {string} url
 * @param {'GET'|'POST'|'PUT'|'DELETE'} method
 * @param {object|null} body
 * @returns {Promise<{ok: boolean, data: any}>}
 */
async function apiFetch(url, method = 'GET', body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body !== null) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    let data;
    try { data = await res.json(); } catch { data = null; }
    return { ok: res.ok, status: res.status, data };
}

/**
 * Show a transient toast notification.
 * @param {string} message
 * @param {'success'|'error'|'info'} type
 */
function showToast(message, type = 'info') {
    const existing = document.getElementById('has-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'has-toast';
    toast.textContent = message;
    Object.assign(toast.style, {
        position: 'fixed',
        bottom: '1.5rem',
        right: '1.5rem',
        background: type === 'success' ? 'var(--success)' : type === 'error' ? 'var(--danger)' : 'var(--accent)',
        color: type === 'success' || type === 'error' ? '#000' : '#fff',
        padding: '0.75rem 1.25rem',
        borderRadius: '8px',
        fontWeight: '600',
        fontSize: '0.9rem',
        zIndex: '9999',
        boxShadow: 'var(--shadow)',
        transition: 'opacity 0.3s',
    });
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 350);
    }, 3000);
}

