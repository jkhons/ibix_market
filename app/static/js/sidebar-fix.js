/**
 * Sidebar fix - PDV Ibix
 * 1. Garante sidebar sempre expandida (remove estado colapsado).
 * 2. Persiste e restaura a posição de scroll da sidebar entre navegações (continuidade de scroll).
 */
(function () {
    'use strict';

    var STORAGE_PREFIX = 'sidebarScrollY';
    var DEBOUNCE_MS = 150;
    var ACTIVE_SCROLL_THRESHOLD_PX = 80; // só faz scrollIntoView do .active se estiver a mais de 80px fora da vista

    function getScrollStorageKey() {
        var pathname = window.location.pathname || '/';
        var role = '';
        var tenant = '';
        var body = document.body;
        if (body && body.getAttribute) {
            role = (body.getAttribute('data-user-role') || '').trim();
            tenant = (body.getAttribute('data-tenant') || '').trim();
        }
        var parts = [STORAGE_PREFIX, pathname];
        if (role) parts.push(role);
        if (tenant) parts.push(tenant);
        return parts.join(':');
    }

    function getScrollableElement() {
        var sidebar = document.querySelector('.sidebar, .js-sidebar');
        if (!sidebar) return null;
        return sidebar.querySelector('.sidebar-content') || null;
    }

    function saveScroll() {
        var el = getScrollableElement();
        if (!el) return;
        var key = getScrollStorageKey();
        try {
            sessionStorage.setItem(key, String(el.scrollTop));
        } catch (e) {}
    }

    function debounce(fn, ms) {
        var t;
        return function () {
            var a = arguments;
            clearTimeout(t);
            t = setTimeout(function () { fn.apply(null, a); }, ms);
        };
    }

    function shouldSaveOnClick(ev) {
        if (ev.ctrlKey || ev.metaKey || ev.shiftKey) return false;
        if (ev.button !== 0) return false;
        var a = ev.target && ev.target.closest ? ev.target.closest('a') : null;
        if (!a) return false;
        if (a.target === '_blank') return false;
        var href = (a.getAttribute('href') || '').trim();
        if (href === '' || href === '#') return false;
        if (href.charAt(0) === '#') return false;
        try {
            var url = new URL(href, window.location.href);
            if (url.host !== window.location.host) return false;
        } catch (e) {
            return false;
        }
        return true;
    }

    function restoreScroll(allowRestoreFromBfcache) {
        var el = getScrollableElement();
        if (!el) return;
        if (allowRestoreFromBfcache === false && el.scrollTop !== 0) return;
        var key = getScrollStorageKey();
        var value;
        try {
            value = sessionStorage.getItem(key);
        } catch (e) { return; }
        if (value === null || value === '') return;
        var top = parseInt(value, 10);
        if (isNaN(top) || top < 0) return;
        requestAnimationFrame(function () {
            el.scrollTop = top;
            ensureActiveVisible(el);
        });
    }

    function ensureActiveVisible(container) {
        if (!container) container = getScrollableElement();
        if (!container) return;
        var active = container.querySelector('.sidebar-item.active');
        if (!active) return;
        var cr = container.getBoundingClientRect();
        var ar = active.getBoundingClientRect();
        var topInView = ar.top >= cr.top - ACTIVE_SCROLL_THRESHOLD_PX;
        var bottomInView = ar.bottom <= cr.bottom + ACTIVE_SCROLL_THRESHOLD_PX;
        if (topInView && bottomInView) return;
        var distance = Math.abs(ar.top - cr.top);
        if (distance < ACTIVE_SCROLL_THRESHOLD_PX) return;
        active.scrollIntoView({ block: 'nearest', behavior: 'auto' });
    }

    function initScrollPersistence() {
        var scrollable = getScrollableElement();
        if (!scrollable) return;

        var saveDebounced = debounce(saveScroll, DEBOUNCE_MS);
        scrollable.addEventListener('scroll', saveDebounced, { passive: true });

        var sidebar = document.querySelector('.sidebar, .js-sidebar');
        if (sidebar) {
            sidebar.addEventListener('click', function (ev) {
                if (shouldSaveOnClick(ev)) saveScroll();
            }, true);
        }

        window.addEventListener('pagehide', saveScroll);
    }

    function onDOMContentLoaded() {
        requestAnimationFrame(function () {
            restoreScroll(true);
        });
        initScrollPersistence();
    }

    function onPageshow(ev) {
        if (ev.persisted) {
            var el = getScrollableElement();
            if (el && el.scrollTop === 0) restoreScroll(true);
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        console.log('Sidebar Fix - Garantindo que a sidebar sempre inicie expandida...');

        if (localStorage.getItem('sidebar-collapsed') === 'true') {
            localStorage.removeItem('sidebar-collapsed');
            console.log('Estado colapsado removido do localStorage');
        }

        var sidebar = document.querySelector('.js-sidebar');
        var main = document.querySelector('.main');
        var sidebarToggle = document.querySelector('.js-sidebar-toggle');

        if (sidebar) {
            sidebar.classList.remove('collapsed');
            console.log('Classe collapsed removida da sidebar');
        }
        if (main) {
            main.classList.remove('sidebar-collapsed');
            console.log('Classe sidebar-collapsed removida do main');
        }
        if (sidebarToggle) {
            sidebarToggle.classList.remove('active');
            console.log('Classe active removida do botão toggle');
        }

        onDOMContentLoaded();
        console.log('Sidebar Fix aplicado com sucesso!');
    });

    window.addEventListener('pageshow', onPageshow);
})();
