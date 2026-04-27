/**
 * Prepare sua Vitrine - Página de correção de pendências
 * Lista produtos sem imagem, tipo ou categoria e permite corrigir na própria página.
 */
var PendenciasEstoque = (function() {
    var MAX_IMAGENS_UI = 12;
    var clienteId = '';
    var pendenciaAtiva = null;
    var produtosData = [];
    var categoriasList = [];
    var tiposMaterialList = [];
    var stats = { sem_imagem: 0, sem_tipo: 0, sem_categoria: 0, sem_preco_venda: 0, sem_descricao: 0 };
    var correcaoMidias = []; // { tipo, url, file?, base64? }
    var correcaoMidiasFiles = [];
    var produtoCorrecaoAtual = null;

    function getToken() {
        var c = document.cookie.split(';').find(function(x) {
            return x.trim().startsWith('pdv_solumatica_token=') || x.trim().startsWith('pdv_automscale_token=');
        });
        return c ? decodeURIComponent(c.split('=').slice(1).join('=').trim()) : null;
    }

    function fetchApi(url, opts) {
        var t = getToken();
        var headers = opts && opts.headers || {};
        headers['Accept'] = 'application/json';
        if (t) headers['Authorization'] = 'Bearer ' + t;
        return fetch(url, { credentials: 'include', headers: headers, method: opts && opts.method || 'GET', body: opts && opts.body });
    }

    function carregarStats() {
        if (!clienteId) return;
        fetchApi('/api/v1/produtos-cliente/stats?cliente_id=' + encodeURIComponent(clienteId))
            .then(function(r) { return r.ok ? r.json() : {}; })
            .then(function(data) {
                stats = data || stats;
                var b1 = document.getElementById('badge-sem-imagem');
                var b2 = document.getElementById('badge-sem-tipo');
                var b3 = document.getElementById('badge-sem-categoria');
                var b4 = document.getElementById('badge-sem-preco-venda');
                var b5 = document.getElementById('badge-sem-descricao');
                if (b1) b1.textContent = stats.sem_imagem || 0;
                if (b2) b2.textContent = stats.sem_tipo || 0;
                if (b3) b3.textContent = stats.sem_categoria || 0;
                if (b4) b4.textContent = stats.sem_preco_venda || 0;
                if (b5) b5.textContent = stats.sem_descricao || 0;
            })
            .catch(function() {});
    }

    function carregarCategoriasTipos() {
        Promise.all([
            fetchApi('/api/v1/material-categorias/?limit=500').then(function(r) { return r.ok ? r.json() : []; }),
            fetchApi('/api/v1/tipo-material/?limit=500').then(function(r) { return r.ok ? r.json() : []; })
        ]).then(function(res) {
            categoriasList = res[0] || [];
            tiposMaterialList = res[1] || [];
        }).catch(function() {});
    }

    function selecionarPendencia(tipo) {
        pendenciaAtiva = tipo;
        document.querySelectorAll('.card-pendencia').forEach(function(c) {
            c.classList.toggle('active', c.getAttribute('data-tipo') === tipo);
        });
        var titulos = {
            sem_imagem: 'Produtos sem imagens',
            sem_tipo: 'Produtos sem tipo',
            sem_categoria: 'Produtos sem categoria',
            sem_preco_venda: 'Produtos sem preço de venda',
            sem_descricao: 'Produtos sem descrição'
        };
        var titulo = document.getElementById('titulo-lista-pendencia');
        if (titulo) titulo.textContent = titulos[tipo] || 'Produtos para corrigir';
        document.getElementById('secao-produtos').style.display = 'block';
        carregarProdutosPendencia();
    }

    function fecharListaProdutos() {
        pendenciaAtiva = null;
        document.querySelectorAll('.card-pendencia').forEach(function(c) { c.classList.remove('active'); });
        document.getElementById('secao-produtos').style.display = 'none';
    }

    async function carregarProdutosPendencia() {
        if (!clienteId || !pendenciaAtiva) return;
        var params = new URLSearchParams({ cliente_id: clienteId, limit: '500' });
        if (pendenciaAtiva === 'sem_imagem') params.set('sem_imagem', 'true');
        if (pendenciaAtiva === 'sem_tipo') params.set('sem_tipo', 'true');
        if (pendenciaAtiva === 'sem_categoria') params.set('sem_categoria', 'true');
        if (pendenciaAtiva === 'sem_preco_venda') params.set('sem_preco_venda', 'true');
        if (pendenciaAtiva === 'sem_descricao') params.set('sem_descricao', 'true');
        var tbody = document.getElementById('tabela-produtos-pendencias');
        tbody.innerHTML = '<tr><td colspan="6" class="text-center"><div class="spinner-border spinner-border-sm"></div> Carregando...</td></tr>';
        try {
            var r = await fetchApi('/api/v1/produtos-cliente/?' + params.toString());
            var data = r.ok ? await r.json() : { items: [] };
            produtosData = data.items || [];
            renderizarTabela();
        } catch (e) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Erro ao carregar.</td></tr>';
        }
        if (typeof feather !== 'undefined') feather.replace();
    }

    function renderizarTabela() {
        var tbody = document.getElementById('tabela-produtos-pendencias');
        if (!tbody) return;
        if (produtosData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Nenhum produto encontrado.</td></tr>';
            return;
        }
        tbody.innerHTML = produtosData.map(function(p) {
            var cat = (categoriasList.find(function(c) { return c.id == p.categoria_id; }) || {}).nome || '—';
            var tip = (tiposMaterialList.find(function(t) { return t.id == p.tipo_material_id; }) || {}).nome || '—';
            var valorVenda = (p.valor_venda !== null && p.valor_venda !== undefined) ? Number(p.valor_venda).toFixed(2).replace('.', ',') : '—';
            return '<tr><td><strong>' + (p.codigo || '').replace(/</g, '&lt;') + '</strong></td>' +
                '<td>' + (p.nome || '').replace(/</g, '&lt;') + '</td>' +
                '<td>' + cat.replace(/</g, '&lt;') + '</td>' +
                '<td>' + tip.replace(/</g, '&lt;') + '</td>' +
                '<td>R$ ' + valorVenda + '</td>' +
                '<td><button type="button" class="btn btn-sm btn-warning" onclick="PendenciasEstoque.abrirCorrecao(' + p.id + ')"><i data-feather="edit-2" style="width:14px;height:14px;"></i> Corrigir</button></td></tr>';
        }).join('');
        if (typeof feather !== 'undefined') feather.replace();
    }

    function abrirCorrecao(produtoId) {
        var prod = produtosData.find(function(p) { return p.id == produtoId; });
        if (!prod) return;
        produtoCorrecaoAtual = prod;
        document.getElementById('correcao_produto_id').value = produtoId;
        document.getElementById('correcao_pendencia_tipo').value = pendenciaAtiva;

        document.getElementById('bloco-categoria').style.display = (pendenciaAtiva === 'sem_categoria') ? 'block' : 'none';
        document.getElementById('bloco-tipo').style.display = (pendenciaAtiva === 'sem_tipo') ? 'block' : 'none';
        document.getElementById('bloco-imagens').style.display = (pendenciaAtiva === 'sem_imagem') ? 'block' : 'none';
        document.getElementById('bloco-preco-venda').style.display = (pendenciaAtiva === 'sem_preco_venda') ? 'block' : 'none';
        document.getElementById('bloco-descricao').style.display = (pendenciaAtiva === 'sem_descricao') ? 'block' : 'none';

        var selCat = document.getElementById('correcao_categoria_id');
        var selTipo = document.getElementById('correcao_tipo_material_id');
        selCat.innerHTML = '<option value="">Selecione...</option>' + (categoriasList.map(function(c) {
            return '<option value="' + c.id + '"' + (c.id == prod.categoria_id ? ' selected' : '') + '>' + (c.nome || '').replace(/</g, '&lt;') + '</option>';
        }).join(''));
        selTipo.innerHTML = '<option value="">Selecione...</option>' + (tiposMaterialList.map(function(t) {
            return '<option value="' + t.id + '"' + (t.id == prod.tipo_material_id ? ' selected' : '') + '>' + (t.nome || '').replace(/</g, '&lt;') + '</option>';
        }).join(''));

        correcaoMidias = [];
        correcaoMidiasFiles = [];
        if (prod.foto_peca && String(prod.foto_peca).trim()) {
            correcaoMidias.push({ tipo: 'imagem', url: prod.foto_peca.startsWith('uploads/') ? prod.foto_peca : 'uploads/produtos/' + prod.foto_peca.replace(/^.*?uploads\/produtos\//, '') });
        }
        if (prod.midias && Array.isArray(prod.midias)) {
            prod.midias.forEach(function(m) {
                if (m && m.url) correcaoMidias.push({ tipo: (m.tipo || 'imagem').toLowerCase(), url: m.url });
            });
        }
        renderCorrecaoMidias();
        document.getElementById('correcao_youtube_input').value = '';
        var inpImagemUrl = document.getElementById('correcao_imagem_url_input');
        if (inpImagemUrl) inpImagemUrl.value = '';
        var inpPrecoVenda = document.getElementById('correcao_valor_venda');
        if (inpPrecoVenda) {
            inpPrecoVenda.value = (prod.valor_venda !== null && prod.valor_venda !== undefined && Number(prod.valor_venda) > 0) ? Number(prod.valor_venda).toFixed(2) : '';
        }
        var taDesc = document.getElementById('correcao_descricao');
        if (taDesc) taDesc.value = (prod.descricao != null && prod.descricao !== undefined) ? String(prod.descricao) : '';
        document.getElementById('correcao_midias_file').value = '';
        document.getElementById('modalCorrecaoTitulo').textContent = (prod.nome || prod.codigo || 'Produto');
        document.getElementById('modalCorrecaoPendencia').style.display = 'block';
        document.body.style.overflow = 'hidden';
        if (typeof feather !== 'undefined') feather.replace();
    }

    function fecharModalCorrecao() {
        document.getElementById('modalCorrecaoPendencia').style.display = 'none';
        document.body.style.overflow = '';
        produtoCorrecaoAtual = null;
    }

    function buscarGoogleProdutoCorrecao() {
        if (!produtoCorrecaoAtual) return;
        var termoBase = (produtoCorrecaoAtual.descricao || '').trim();
        if (!termoBase) termoBase = (produtoCorrecaoAtual.nome || '').trim();
        if (!termoBase) termoBase = (produtoCorrecaoAtual.codigo || '').trim();
        if (!termoBase) {
            alert('Produto sem descrição/nome para buscar.');
            return;
        }
        var url = 'https://www.google.com/search?tbm=isch&q=' + encodeURIComponent(termoBase);
        window.open(url, '_blank', 'noopener,noreferrer');
    }

    async function copiarNomeProdutoCorrecao() {
        if (!produtoCorrecaoAtual || !produtoCorrecaoAtual.nome) {
            alert('Nome do produto não encontrado.');
            return;
        }
        var nome = String(produtoCorrecaoAtual.nome);
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(nome);
                return;
            }
        } catch (e) {}
        var ta = document.createElement('textarea');
        ta.value = nome;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        try { document.execCommand('copy'); } catch (e2) {}
        document.body.removeChild(ta);
    }

    function extrairYoutubeEmbed(input) {
        var s = (input || '').trim();
        var m = s.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/);
        return m ? 'https://www.youtube.com/embed/' + m[1] : null;
    }

    function adicionarYoutubeCorrecao() {
        var inp = document.getElementById('correcao_youtube_input');
        var url = extrairYoutubeEmbed(inp ? inp.value : '');
        if (!url) { alert('Informe um link válido do YouTube.'); return; }
        correcaoMidias.push({ tipo: 'youtube', url: url });
        if (inp) inp.value = '';
        renderCorrecaoMidias();
    }

    function adicionarImagemUrlCorrecao() {
        var inp = document.getElementById('correcao_imagem_url_input');
        var raw = inp ? String(inp.value || '').trim() : '';
        if (!raw) {
            alert('Informe o link da imagem.');
            return;
        }
        if (!/^https?:\/\//i.test(raw)) {
            alert('Informe uma URL válida iniciando com http:// ou https://');
            return;
        }
        var jaExiste = correcaoMidias.some(function(m) {
            return (m.tipo || '').toLowerCase() === 'imagem' && m.url && String(m.url).trim().toLowerCase() === raw.toLowerCase();
        });
        if (jaExiste) {
            alert('Esse link já foi adicionado.');
            return;
        }
        var nImgAtual = correcaoMidias.filter(function(m) { return (m.tipo || '').toLowerCase() === 'imagem'; }).length;
        if (nImgAtual >= MAX_IMAGENS_UI) {
            alert('Máximo de ' + MAX_IMAGENS_UI + ' imagens.');
            return;
        }
        correcaoMidias.push({ tipo: 'imagem', url: raw });
        if (inp) inp.value = '';
        renderCorrecaoMidias();
    }

    function renderCorrecaoMidias() {
        var cont = document.getElementById('correcao_midias_list');
        if (!cont) return;
        cont.innerHTML = '';
        correcaoMidias.forEach(function(m, i) {
            var div = document.createElement('div');
            div.className = 'position-relative';
            div.style.width = '80px';
            var tipo = (m.tipo || 'imagem').toLowerCase();
            var url = m.url && m.url.startsWith('http') ? m.url : (m.url ? '/static/' + m.url : '');
            var src = m.file ? URL.createObjectURL(m.file) : (m.base64 || url);
            if (tipo === 'youtube') {
                var vidId = (m.url || '').match(/(?:embed\/|v=|\/)([a-zA-Z0-9_-]{11})/);
                src = 'https://img.youtube.com/vi/' + (vidId ? vidId[1] : '') + '/default.jpg';
            }
            div.innerHTML = '<img src="' + src + '" alt="" style="width:80px;height:60px;object-fit:cover;border-radius:6px;" class="border">' +
                '<button type="button" class="btn btn-sm btn-danger position-absolute top-0 end-0 m-0 p-0" style="width:20px;height:20px;font-size:11px;" data-idx="' + i + '">&times;</button>';
            cont.appendChild(div);
        });
        cont.querySelectorAll('[data-idx]').forEach(function(btn) {
            btn.onclick = function() {
                correcaoMidias.splice(parseInt(btn.getAttribute('data-idx'), 10), 1);
                renderCorrecaoMidias();
            };
        });
        if (typeof feather !== 'undefined') feather.replace();
    }

    function fileToDataUrl(file) {
        return new Promise(function(res, rej) {
            var r = new FileReader();
            r.onload = function() { res(r.result); };
            r.onerror = rej;
            r.readAsDataURL(file);
        });
    }

    async function salvarCorrecaoPendencia() {
        var id = document.getElementById('correcao_produto_id').value;
        var tipo = document.getElementById('correcao_pendencia_tipo').value;
        if (!id || !getToken()) return;
        var btn = document.getElementById('btnSalvarCorrecao');
        if (btn) { btn.disabled = true; btn.textContent = 'Salvando...'; }
        var payload = {};
        if (tipo === 'sem_categoria') {
            var cat = document.getElementById('correcao_categoria_id').value;
            if (!cat) { alert('Selecione uma categoria.'); if (btn) { btn.disabled = false; btn.textContent = 'Salvar correção'; } return; }
            payload.categoria_id = parseInt(cat, 10);
        }
        if (tipo === 'sem_tipo') {
            var tip = document.getElementById('correcao_tipo_material_id').value;
            if (!tip) { alert('Selecione um tipo de material.'); if (btn) { btn.disabled = false; btn.textContent = 'Salvar correção'; } return; }
            payload.tipo_material_id = parseInt(tip, 10);
        }
        if (tipo === 'sem_imagem') {
            if (correcaoMidias.length === 0) {
                alert('Adicione ao menos uma imagem ao produto.');
                if (btn) { btn.disabled = false; btn.textContent = 'Salvar correção'; }
                return;
            }
            var firstImg = correcaoMidias.find(function(m) { return (m.tipo || '').toLowerCase() === 'imagem'; });
            var prodAtual = {};
            if (firstImg && (firstImg.file || firstImg.base64)) {
                payload.foto_peca_base64 = firstImg.base64 || (firstImg.file ? await fileToDataUrl(firstImg.file) : null);
                var r1 = await fetchApi('/api/v1/produtos-cliente/' + id, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                prodAtual = r1.ok ? await r1.json() : {};
            } else {
                var r0 = await fetchApi('/api/v1/produtos-cliente/' + id);
                prodAtual = r0.ok ? await r0.json() : {};
            }
            var filesToUpload = correcaoMidias.filter(function(m) { return m.file; });
            if (filesToUpload.length > 0) {
                var fd = new FormData();
                filesToUpload.forEach(function(m) { fd.append('files', m.file); });
                var mResp = await fetchApi('/api/v1/produtos-cliente/' + id + '/midias', { method: 'POST', body: fd });
                prodAtual = mResp.ok ? await mResp.json() : prodAtual;
            }
            var imageUrlExternas = correcaoMidias.filter(function(m) {
                return (m.tipo || '').toLowerCase() === 'imagem' && m.url && /^https?:\/\//i.test(m.url);
            });
            if (imageUrlExternas.length > 0) {
                var importedByExternal = {};
                for (var i = 0; i < imageUrlExternas.length; i++) {
                    if (importedByExternal[imageUrlExternas[i].url]) {
                        imageUrlExternas[i].url = importedByExternal[imageUrlExternas[i].url];
                        continue;
                    }
                    var rImp = await fetchApi('/api/v1/produtos-cliente/' + id + '/midias/import-url', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: imageUrlExternas[i].url })
                    });
                    if (!rImp.ok) {
                        var errImp = await rImp.json().catch(function() { return {}; });
                        throw new Error(errImp.detail || 'Falha ao importar imagem por link');
                    }
                    prodAtual = await rImp.json().catch(function() { return prodAtual; });
                    var midiasResp = Array.isArray(prodAtual.midias) ? prodAtual.midias : [];
                    var ultimaImagemInterna = null;
                    for (var k = midiasResp.length - 1; k >= 0; k--) {
                        var mk = midiasResp[k];
                        if (mk && (mk.tipo || '').toLowerCase() === 'imagem' && mk.url && !/^https?:\/\//i.test(mk.url)) {
                            ultimaImagemInterna = mk.url;
                            break;
                        }
                    }
                    if (ultimaImagemInterna) {
                        importedByExternal[imageUrlExternas[i].url] = ultimaImagemInterna;
                    }
                }
            }
            var midiasPayload = [];
            if (prodAtual.foto_peca) midiasPayload.push({ tipo: 'imagem', url: prodAtual.foto_peca });
            if (prodAtual.midias && Array.isArray(prodAtual.midias)) {
                prodAtual.midias.forEach(function(m) { if (m && m.url) midiasPayload.push({ tipo: (m.tipo || 'imagem').toLowerCase(), url: m.url }); });
            }
            correcaoMidias.filter(function(m) {
                var tipoMidia = (m.tipo || '').toLowerCase();
                var isImagemExterna = tipoMidia === 'imagem' && /^https?:\/\//i.test(m.url || '');
                return m.url && (tipoMidia === 'youtube' || (tipoMidia === 'imagem' && !isImagemExterna));
            }).forEach(function(m) {
                midiasPayload.push({ tipo: (m.tipo || 'imagem').toLowerCase(), url: m.url });
            });
            var seen = {};
            midiasPayload = midiasPayload.filter(function(m) {
                if (!m || !m.url) return false;
                var key = String((m.tipo || 'imagem').toLowerCase()) + '|' + String(m.url).trim();
                if (seen[key]) return false;
                seen[key] = true;
                return true;
            });
            var firstImgUrl = (midiasPayload.find(function(m) { return (m.tipo || '').toLowerCase() === 'imagem'; }) || {}).url || null;
            payload = { midias: midiasPayload, foto_peca: firstImgUrl };
        }
        if (tipo === 'sem_preco_venda') {
            var valorInput = document.getElementById('correcao_valor_venda');
            var valorStr = valorInput ? String(valorInput.value || '').trim() : '';
            var valor = Number(valorStr);
            if (!valorStr || !Number.isFinite(valor) || valor <= 0) {
                alert('Informe um preço de venda válido maior que zero.');
                if (btn) { btn.disabled = false; btn.textContent = 'Salvar correção'; }
                return;
            }
            payload.valor_venda = valor;
        }
        if (tipo === 'sem_descricao') {
            var ta = document.getElementById('correcao_descricao');
            var txt = ta ? String(ta.value || '').trim() : '';
            if (!txt) {
                alert('Informe a descrição do produto.');
                if (btn) { btn.disabled = false; btn.textContent = 'Salvar correção'; }
                return;
            }
            payload.descricao = txt;
        }
        try {
            var r = await fetchApi('/api/v1/produtos-cliente/' + id, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (r.ok) {
                fecharModalCorrecao();
                carregarProdutosPendencia();
                carregarStats();
            } else {
                var err = await r.json().catch(function() { return {}; });
                alert('Erro: ' + (err.detail || r.status));
            }
        } catch (e) {
            alert('Erro ao salvar.');
        }
        if (btn) { btn.disabled = false; btn.textContent = 'Salvar correção'; }
    }

    return {
        init: function() {
            clienteId = (document.getElementById('estoque_cliente_id') || {}).value || '';
            if (!clienteId) return;
            carregarStats();
            carregarCategoriasTipos();
            document.querySelectorAll('.card-pendencia').forEach(function(c) {
                c.addEventListener('click', function() {
                    selecionarPendencia(c.getAttribute('data-tipo'));
                });
            });
            document.getElementById('correcao_midias_file').addEventListener('change', function() {
                var files = this.files;
                if (!files || !files.length) return;
                for (var i = 0; i < files.length; i++) {
                    var f = files[i];
                    var isVid = f.type && f.type.indexOf('video') !== -1;
                    correcaoMidias.push({ tipo: isVid ? 'video' : 'imagem', file: f });
                }
                this.value = '';
                renderCorrecaoMidias();
            });
            var midiasArea = document.getElementById('correcao_midias_area');
            function onPasteImagem(e) {
                var modal = document.getElementById('modalCorrecaoPendencia');
                var blocoImg = document.getElementById('bloco-imagens');
                if (!modal || modal.style.display === 'none' || !blocoImg || blocoImg.style.display === 'none') return;
                var items = (e.clipboardData && e.clipboardData.items) ? e.clipboardData.items : [];
                var nImgAtual = correcaoMidias.filter(function(m) { return (m.tipo || '').toLowerCase() === 'imagem'; }).length;
                var adicionou = false;
                for (var i = 0; i < items.length && nImgAtual < MAX_IMAGENS_UI; i++) {
                    if (items[i].type && items[i].type.indexOf('image') !== -1) {
                        e.preventDefault();
                        adicionou = true;
                        var f = items[i].getAsFile();
                        if (f) {
                            correcaoMidias.push({ tipo: 'imagem', file: f });
                            nImgAtual++;
                            renderCorrecaoMidias();
                        }
                    }
                }
                if (adicionou && nImgAtual >= MAX_IMAGENS_UI) {
                    alert('Máximo de ' + MAX_IMAGENS_UI + ' imagens.');
                }
            }
            if (midiasArea) midiasArea.addEventListener('paste', onPasteImagem);
            document.addEventListener('paste', onPasteImagem);
            if (typeof feather !== 'undefined') feather.replace();
        },
        abrirCorrecao: abrirCorrecao,
        fecharListaProdutos: fecharListaProdutos,
        fecharModalCorrecao: fecharModalCorrecao,
        salvarCorrecaoPendencia: salvarCorrecaoPendencia,
        adicionarYoutubeCorrecao: adicionarYoutubeCorrecao,
        adicionarImagemUrlCorrecao: adicionarImagemUrlCorrecao,
        buscarGoogleProdutoCorrecao: buscarGoogleProdutoCorrecao,
        copiarNomeProdutoCorrecao: copiarNomeProdutoCorrecao
    };
})();
