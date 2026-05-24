// PolicyLens AI - Main JS

document.addEventListener('DOMContentLoaded', function () {

    const sidebar   = document.getElementById('sidebar');
    const content   = document.getElementById('content');
    const toggleBtn = document.getElementById('sidebarToggle');
    const overlay   = document.getElementById('sidebarOverlay');

    // ── SIDEBAR LOGIC ────────────────────────────────────
    function isMobile() {
        return window.innerWidth <= 768;
    }

    function openSidebar() {
        sidebar.classList.remove('sidebar-collapsed');
        content.classList.remove('content-expanded');
        if (isMobile() && overlay) {
            overlay.classList.add('active');
        }
    }

    function closeSidebar() {
        sidebar.classList.add('sidebar-collapsed');
        content.classList.add('content-expanded');
        if (overlay) overlay.classList.remove('active');
    }

    // Set initial state
    if (sidebar && content) {
        if (isMobile()) {
            // Mobile: start with sidebar hidden
            sidebar.classList.add('sidebar-collapsed');
            content.classList.add('content-expanded');
        } else {
            // Desktop: start with sidebar visible
            sidebar.classList.remove('sidebar-collapsed');
            content.classList.remove('content-expanded');
        }
    }

    // Toggle button click
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (sidebar.classList.contains('sidebar-collapsed')) {
                openSidebar();
            } else {
                closeSidebar();
            }
        });
    }

    // Click overlay to close on mobile
    if (overlay) {
        overlay.addEventListener('click', function () {
            closeSidebar();
        });
    }

    // Handle window resize
    window.addEventListener('resize', function () {
        if (!isMobile()) {
            openSidebar();
            if (overlay) overlay.classList.remove('active');
        } else {
            closeSidebar();
        }
    });

    // ── GLOBAL CUSTOM CONFIRM MODAL ──────────────────────
    // Usage: showConfirm({ title, message, btnText, btnClass, onConfirm })
    window.showConfirm = function(options) {
        const modal      = document.getElementById('confirmModal');
        const titleEl    = document.getElementById('confirmTitle');
        const messageEl  = document.getElementById('confirmMessage');
        const okBtn      = document.getElementById('confirmOkBtn');
        const iconEl     = document.getElementById('confirmIcon');

        titleEl.textContent   = options.title   || 'Are you sure?';
        messageEl.textContent = options.message || '';
        okBtn.textContent     = options.btnText || 'Confirm';
        okBtn.className       = 'btn px-4 ' + (options.btnClass || 'btn-danger');
        iconEl.className      = 'confirm-modal-icon mb-3 ' + (options.iconClass || 'icon-warning');

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        // Remove old listener and add new one
        const newBtn = okBtn.cloneNode(true);
        newBtn.textContent = options.btnText || 'Confirm';
        newBtn.className   = 'btn px-4 ' + (options.btnClass || 'btn-danger');
        okBtn.parentNode.replaceChild(newBtn, okBtn);

        newBtn.addEventListener('click', function() {
            bsModal.hide();
            if (options.onConfirm) options.onConfirm();
        });
    };


    const logoutBtn   = document.getElementById('logoutBtn');
    const logoutModal = document.getElementById('logoutModal');

    if (logoutBtn && logoutModal) {
        logoutBtn.addEventListener('click', function (e) {
            e.preventDefault();
            const modal = new bootstrap.Modal(logoutModal);
            modal.show();
        });
    }

    // ── DARK / LIGHT THEME TOGGLE ────────────────────────
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon   = document.getElementById('themeIcon');

    function applyTheme(theme) {
        if (theme === 'dark') {
            document.body.classList.add('dark-mode');
            if (themeIcon) {
                themeIcon.classList.remove('bi-moon-fill');
                themeIcon.classList.add('bi-sun-fill');
            }
        } else {
            document.body.classList.remove('dark-mode');
            if (themeIcon) {
                themeIcon.classList.remove('bi-sun-fill');
                themeIcon.classList.add('bi-moon-fill');
            }
        }
        localStorage.setItem('pl_theme', theme);
    }

    // Apply saved theme immediately on load
    const savedTheme = localStorage.getItem('pl_theme') || 'light';
    applyTheme(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            const current = localStorage.getItem('pl_theme') || 'light';
            applyTheme(current === 'light' ? 'dark' : 'light');
        });
    }

    // ── AUTO-DISMISS TOAST NOTIFICATIONS (4.5s) ──────────
    document.querySelectorAll('.toast-notification').forEach(function (toast) {
        setTimeout(function () {
            toast.style.transition = 'opacity 0.4s ease';
            toast.style.opacity = '0';
            setTimeout(function() {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 400);
        }, 4500);
    });

    // ── STAT COUNTER ANIMATION ───────────────────────────
    document.querySelectorAll('.stat-value').forEach(function (el) {
        const text      = el.textContent.trim();
        const isPercent = text.includes('%');
        const num       = parseInt(text.replace('%', ''));
        if (isNaN(num) || num === 0) return;

        let current = 0;
        const step  = Math.max(1, Math.ceil(num / 30));
        const timer = setInterval(function () {
            current += step;
            if (current >= num) {
                current = num;
                clearInterval(timer);
            }
            el.textContent = isPercent ? current + '%' : current;
        }, 30);
    });

    // ── DRAG AND DROP UPLOAD ─────────────────────────────
    const dropZone  = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    if (dropZone && fileInput) {
        dropZone.addEventListener('dragover', function (e) {
            e.preventDefault();
            dropZone.style.borderColor = '#4361ee';
            dropZone.style.background  = '#f0f4ff';
        });
        dropZone.addEventListener('dragleave', function () {
            dropZone.style.borderColor = '';
            dropZone.style.background  = '';
        });
        dropZone.addEventListener('drop', function (e) {
            e.preventDefault();
            dropZone.style.borderColor = '';
            dropZone.style.background  = '';
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                fileInput.dispatchEvent(new Event('change'));
            }
        });
    }

});
