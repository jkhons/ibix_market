/**
 * Impressão de cupom do caixa (vendas PDV).
 * Mesmo fluxo de Negócio > Pedidos, com largura fixa em mm para bobina térmica 80 mm.
 */
(function (global) {
    'use strict';

    var STYLE_ID = 'cupom-caixa-print-style';
    var AREA_ID = 'cupom-caixa-print-area';

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function larguraMm(data) {
        var mm = Number(data && data.largura_mm);
        return mm === 58 ? 58 : 80;
    }

    function ensurePrintStyles(larguraMmValue) {
        var contentMm = larguraMmValue - 8;
        var css = [
            '@page { size: ' + larguraMmValue + 'mm auto; margin: 2mm; }',
            '@media print {',
            '  body * { visibility: hidden !important; }',
            '  #' + AREA_ID + ', #' + AREA_ID + ' * { visibility: visible !important; }',
            '  #' + AREA_ID + ' {',
            '    position: absolute !important;',
            '    left: 0 !important;',
            '    top: 0 !important;',
            '    width: ' + contentMm + 'mm !important;',
            '    max-width: ' + contentMm + 'mm !important;',
            '    margin: 0 !important;',
            '  }',
            '  #modalDetalhesVenda { display: none !important; }',
            '}'
        ].join('\n');
        var st = document.getElementById(STYLE_ID);
        if (!st) {
            st = document.createElement('style');
            st.id = STYLE_ID;
            document.head.appendChild(st);
        }
        st.textContent = css;
    }

    function imprimirResposta(data) {
        if (!data) {
            alert('Sem conteúdo para impressão.');
            return;
        }
        var hasContent = (data.html && String(data.html).trim()) ||
            (Array.isArray(data.linhas) && data.linhas.length > 0);
        if (!hasContent) {
            alert('Sem conteúdo para impressão.');
            return;
        }

        var mm = larguraMm(data);
        ensurePrintStyles(mm);

        var el = document.getElementById(AREA_ID);
        if (!el) {
            el = document.createElement('div');
            el.id = AREA_ID;
            el.setAttribute('aria-hidden', 'true');
            el.style.cssText = 'position:absolute;left:-9999px;top:0;';
            document.body.appendChild(el);
        }

        if (data.html && String(data.html).trim()) {
            el.innerHTML = data.html;
        } else {
            el.innerHTML = data.linhas.map(function (l) {
                return '<div>' + escapeHtml(l == null ? '' : l) + '</div>';
            }).join('');
        }

        var modal = document.getElementById('modalDetalhesVenda');
        var modalDisplay = modal ? modal.style.display : '';
        if (modal) modal.style.display = 'none';

        var restoreModal = function() {
            if (modal) modal.style.display = modalDisplay || 'block';
            window.removeEventListener('afterprint', restoreModal);
        };
        window.addEventListener('afterprint', restoreModal);

        window.print();
    }

    function imprimirVenda(vendaId, fetchFn) {
        var fn = fetchFn || global.authenticatedFetch || global.fetch;
        return fn('/api/v1/vendas/' + vendaId + '/cupom', {
            credentials: 'include',
            headers: { Accept: 'application/json' }
        }).then(function (r) {
            if (!r.ok) {
                return r.json().catch(function () { return {}; }).then(function (err) {
                    throw new Error(err.detail || 'Erro ao obter cupom da venda.');
                });
            }
            return r.json();
        }).then(function (data) {
            imprimirResposta(data);
        });
    }

    global.PdvCupomCaixa = {
        imprimirResposta: imprimirResposta,
        imprimirVenda: imprimirVenda
    };
})(window);
