/**
 * Referências de documentos — exibição compacta (V-26-57 em vez de VENDA-2026-000057).
 */
(function (global) {
    'use strict';

    var PATTERN = /^(VENDA|V|OS|ORC|PED)-(\d{2,4})-(\d+)$/i;

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function compactDocRef(ref, fallback) {
        if (ref == null || ref === '') {
            return fallback == null ? '—' : fallback;
        }
        var raw = String(ref).trim();
        var match = raw.match(PATTERN);
        if (!match) {
            return raw;
        }
        var prefix = match[1].toUpperCase();
        if (prefix === 'VENDA') {
            prefix = 'V';
        }
        var year = match[2];
        if (year.length === 4) {
            year = year.slice(2);
        }
        return prefix + '-' + year + '-' + String(parseInt(match[3], 10));
    }

    function docRefSpan(ref, options) {
        options = options || {};
        var full = ref == null ? '' : String(ref).trim();
        if (!full) {
            return '<span class="doc-ref text-muted">—</span>';
        }
        var compact = compactDocRef(full);
        var classes = ['doc-ref'];
        if (options.sub) {
            classes.push('doc-ref-sub');
        }
        if (options.className) {
            classes.push(options.className);
        }
        var title = options.title === false ? '' : ' title="' + escapeHtml(full) + '"';
        return '<span class="' + classes.join(' ') + '"' + title + '>' + escapeHtml(compact) + '</span>';
    }

    function docRefOriginLine(tipo, ref) {
        if (!ref) {
            return '';
        }
        var label = tipo || 'Origem';
        return '<br><small class="doc-ref-origin">' + escapeHtml(label) + ' ' + docRefSpan(ref, { sub: true }) + '</small>';
    }

    global.DocRef = {
        compactDocRef: compactDocRef,
        docRefSpan: docRefSpan,
        docRefOriginLine: docRefOriginLine,
        escapeHtml: escapeHtml
    };
})(typeof window !== 'undefined' ? window : this);
