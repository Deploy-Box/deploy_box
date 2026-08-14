/**
 * Unified toast notification system for Deploy Box.
 * Included globally via dashboard_base.html and base.html.
 *
 * Usage:  showToast(message, 'success' | 'error' | 'warning' | 'info')
 */
(function () {
    'use strict';

    const TOAST_DURATION = 4000;
    const ANIMATION_MS = 300;

    let container = null;

    function getContainer() {
        if (!container || !document.body.contains(container)) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className =
                'fixed top-4 right-4 z-[9999] flex flex-col gap-3 pointer-events-none';
            document.body.appendChild(container);
        }
        return container;
    }

    const CONFIG = {
        success: {
            bg: 'bg-emerald-600',
            icon: '<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>',
        },
        error: {
            bg: 'bg-red-600',
            icon: '<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
        },
        warning: {
            bg: 'bg-amber-500',
            icon: '<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4.082a2 2 0 00-3.464 0L3.34 16.082c-.77 1.333.192 3 1.732 3z"/></svg>',
        },
        info: {
            bg: 'bg-blue-600',
            icon: '<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a10 10 0 11-20 0 10 10 0 0120 0z"/></svg>',
        },
    };

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function dismiss(toast) {
        toast.classList.remove('translate-x-0');
        toast.classList.add('translate-x-[120%]');
        setTimeout(() => toast.remove(), ANIMATION_MS);
    }

    function showToast(message, type) {
        type = type || 'info';
        var cfg = CONFIG[type] || CONFIG.info;
        var toast = document.createElement('div');

        toast.className =
            'pointer-events-auto flex items-center gap-3 ' +
            cfg.bg +
            ' text-white px-5 py-3 rounded-lg shadow-xl text-sm font-medium ' +
            'transform transition-all duration-300 translate-x-[120%] max-w-sm';

        toast.innerHTML =
            cfg.icon +
            '<span class="flex-1">' + escapeHtml(String(message)) + '</span>' +
            '<button class="ml-2 text-white/80 hover:text-white flex-shrink-0 text-lg leading-none" aria-label="Close">&times;</button>';

        toast.querySelector('button').addEventListener('click', function () {
            dismiss(toast);
        });

        getContainer().appendChild(toast);

        requestAnimationFrame(function () {
            toast.classList.remove('translate-x-[120%]');
            toast.classList.add('translate-x-0');
        });

        setTimeout(function () {
            dismiss(toast);
        }, TOAST_DURATION);
    }

    window.showToast = showToast;
})();
