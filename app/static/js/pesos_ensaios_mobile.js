/**
 * Pesos Padrão e Ensaios - Mobile Interface
 * Gerencia seleção de conjuntos, composição automática/manual e medições de ensaios
 */

// Estado global
const pesosEnsaiosState = {
    processoId: null,
    balancaId: null,
    conjunto: null,
    conjuntoSalvo: null,
    conjuntoSalvoAplicado: false,
    itens: [],
    cargaAtual: null,
    idsSelecionados: [],
    resumoSelecionado: [],
    composicaoSalva: null,
    pontosDinamicos: [] // Pontos dinâmicos para medições
};

// Tolerância para comparação de soma (0.001 kg)
const TOLERANCIA_SOMA = 0.001;

/**
 * Inicializar módulo de Pesos Padrão e Ensaios
 */
function inicializarPesosEnsaios(processoId, balancaId) {
    pesosEnsaiosState.processoId = processoId;
    pesosEnsaiosState.balancaId = balancaId;
    
    // Resetar estado
    pesosEnsaiosState.conjunto = null;
    pesosEnsaiosState.conjuntoSalvo = null;
    pesosEnsaiosState.conjuntoSalvoAplicado = false;
    pesosEnsaiosState.itens = [];
    pesosEnsaiosState.cargaAtual = null;
    pesosEnsaiosState.idsSelecionados = [];
    pesosEnsaiosState.resumoSelecionado = [];
    pesosEnsaiosState.composicaoSalva = null;
    pesosEnsaiosState.pontosDinamicos = [];
    
    // Aguardar um pouco para garantir que o DOM está pronto
    setTimeout(async () => {
        // Configurar event listeners primeiro
        configurarEventListeners();
        
        // Carregar conjuntos primeiro; depois restaurar conjunto da balança (vínculos peso_padrao); depois medições salvas
        await carregarConjuntos();
        await carregarConjuntoSalvoDaBalança();
        carregarMedicoesSalvas();
    }, 100);
}

/**
 * Restaura o conjunto de pesos a partir dos vínculos da balança (processo_balanca_aux_cadastros, papel=peso_padrao).
 * Independente de medições salvas: ao reabrir o modal, o select e as peças já vêm preenchidos.
 */
async function carregarConjuntoSalvoDaBalança() {
    if (!pesosEnsaiosState.processoId || !pesosEnsaiosState.balancaId) {
        return;
    }
    const getCookieFunc = typeof getCookie !== 'undefined' ? getCookie : function(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    };
    const token = getCookieFunc('pdv_automscale_token');
    if (!token) {
        return;
    }
    try {
        const fetchFn = window.authenticatedFetch || fetch;
        const vinculosRes = await fetchFn(
            `/api/v1/processos/${pesosEnsaiosState.processoId}/balancas/${pesosEnsaiosState.balancaId}/aux-cadastros?papel=peso_padrao`,
            { headers: { 'Authorization': `Bearer ${token}` } }
        );
        if (!vinculosRes.ok) {
            return;
        }
        const vinculos = await vinculosRes.json();
        const primeiro = Array.isArray(vinculos) && vinculos.length > 0 ? vinculos[0] : null;
        const certificadoNumero = primeiro?.aux_cadastro?.certificado_numero || null;
        if (!certificadoNumero) {
            return;
        }
        pesosEnsaiosState.conjuntoSalvo = certificadoNumero;
        const selectConjunto = document.getElementById('pesoConjuntoSelect');
        if (!selectConjunto) {
            return;
        }
        const optionExists = Array.from(selectConjunto.options || []).some(opt => opt.value === certificadoNumero);
        if (!optionExists) {
            return;
        }
        selectConjunto.value = certificadoNumero;
        onConjuntoSelecionado();
        carregarItensConjunto(certificadoNumero);
        pesosEnsaiosState.conjuntoSalvoAplicado = true;
    } catch (e) {
    }
}

/**
 * Carregar medições salvas do banco de dados
 */
async function carregarMedicoesSalvas() {
    if (!pesosEnsaiosState.processoId || !pesosEnsaiosState.balancaId) {
        return;
    }
    
    try {
        const getCookieFunc = typeof getCookie !== 'undefined' ? getCookie : function(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        };
        
        const token = getCookieFunc('pdv_automscale_token');
        if (!token) {
            return;
        }
        
        // Buscar balança para obter equipamento_id
        const fetchFn = window.authenticatedFetch || fetch;
        const balancaResponse = await fetchFn(`/api/v1/processos/${pesosEnsaiosState.processoId}/balancas/${pesosEnsaiosState.balancaId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!balancaResponse.ok) {
            return;
        }
        
        const balanca = await balancaResponse.json();
        
        // SEMPRE restaurar carga e composição do banco (composicao_pesos_atual) quando existir
        const composicao = balanca.composicao_pesos_atual;
        if (composicao && typeof composicao === 'object') {
            const cargaValue = composicao.carga !== null && composicao.carga !== undefined ? parseFloat(composicao.carga) : null;
            if (cargaValue !== null && !Number.isNaN(cargaValue)) {
                pesosEnsaiosState.cargaAtual = cargaValue;
                const cargaInput = document.getElementById('cargaInput');
                if (cargaInput) cargaInput.value = cargaValue.toFixed(3);
            }
            pesosEnsaiosState.idsSelecionados = Array.isArray(composicao.pesos_ids) ? composicao.pesos_ids : [];
            pesosEnsaiosState.resumoSelecionado = Array.isArray(composicao.pesos_resumo) ? composicao.pesos_resumo : [];
            pesosEnsaiosState.composicaoSalva = {
                carga: pesosEnsaiosState.cargaAtual,
                ids: pesosEnsaiosState.idsSelecionados,
                resumo: pesosEnsaiosState.resumoSelecionado
            };
            renderizarComposicao();
        }
        
        // Verificar se há medições salvas (prioridade: ensaio final, depois inicial)
        const medicoesSalvas = balanca.medicoes_final || balanca.medicoes_inicial;
        
        if (medicoesSalvas && Array.isArray(medicoesSalvas) && medicoesSalvas.length > 0) {
            
            const tipoEnsaioSalvo = balanca.tipo_ensaio || (medicoesSalvas[0] && medicoesSalvas[0].tipo_ensaio);
            
            // Fallback Excentricidade: se não havia composicao_pesos_atual, restaurar da primeira medição
            if (tipoEnsaioSalvo === 'excentricidade' && (pesosEnsaiosState.cargaAtual == null || pesosEnsaiosState.idsSelecionados.length === 0)) {
                const ref = medicoesSalvas[0];
                if (ref) {
                    const cargaValue = ref.carga !== null && ref.carga !== undefined ? parseFloat(ref.carga) : null;
                    if (cargaValue !== null && !Number.isNaN(cargaValue)) {
                        pesosEnsaiosState.cargaAtual = cargaValue;
                        const cargaInput = document.getElementById('cargaInput');
                        if (cargaInput) cargaInput.value = cargaValue.toFixed(3);
                    }
                    pesosEnsaiosState.idsSelecionados = Array.isArray(ref.pesos_ids) ? ref.pesos_ids : [];
                    pesosEnsaiosState.resumoSelecionado = Array.isArray(ref.pesos_resumo) ? ref.pesos_resumo : [];
                    pesosEnsaiosState.composicaoSalva = {
                        carga: pesosEnsaiosState.cargaAtual,
                        ids: pesosEnsaiosState.idsSelecionados,
                        resumo: pesosEnsaiosState.resumoSelecionado
                    };
                    if (ref.certificado_numero) pesosEnsaiosState.conjuntoSalvo = ref.certificado_numero;
                    renderizarComposicao();
                }
            }
            
            // Preselecionar tipo de ensaio e renderizar tabela; depois preencher medições
            const tipoEnsaioSelect = document.getElementById('tipoEnsaioSelect');
            if (tipoEnsaioSelect && tipoEnsaioSalvo) {
                tipoEnsaioSelect.value = tipoEnsaioSalvo;
                const blocoMobilidade = document.getElementById('blocoMobilidadePesopadrao');
                if (blocoMobilidade) {
                    blocoMobilidade.style.display = tipoEnsaioSalvo === 'mobilidade' ? 'block' : 'none';
                }
                inicializarPontosDinamicos(tipoEnsaioSalvo);
                renderizarMedicoes(tipoEnsaioSalvo);
                
                if (tipoEnsaioSalvo === 'mobilidade') {
                    carregarCertificadosPESOPADRAO().then(() => {
                        preencherMedicoesSalvas(medicoesSalvas);
                    });
                } else {
                    setTimeout(() => {
                        if (pesosEnsaiosState.cargaAtual != null) {
                            atualizarCargasMedicoes(pesosEnsaiosState.cargaAtual);
                        }
                        preencherMedicoesSalvas(medicoesSalvas);
                    }, 200);
                }
            } else {
                preencherMedicoesSalvas(medicoesSalvas);
            }
        } else {
            // Carga e composição já restauradas acima do banco (composicao_pesos_atual), quando existir
        }
        
    } catch (error) {
        // Não mostrar erro para o usuário, pois não é crítico
    }
}

/**
 * Preencher campos de medições com dados salvos
 */
function preencherMedicoesSalvas(medicoes) {
    if (!medicoes || !Array.isArray(medicoes) || medicoes.length === 0) {
        return;
    }
    
    const tipoEnsaioSelect = document.getElementById('tipoEnsaioSelect');
    const tipoEnsaio = tipoEnsaioSelect?.value;
    
    if (!tipoEnsaio) {
        return;
    }
    
    // Mobilidade: uma linha com Carga, Sobrecarga, Leitura antes, Leitura depois, Padrão utilizado
    if (tipoEnsaio === 'mobilidade') {
        const medicao = medicoes[0];
        const cargaEl = document.getElementById('carga-mobilidade');
        const sobrecargaEl = document.getElementById('sobrecarga-mobilidade');
        const leituraAntesEl = document.getElementById('leitura-antes-mobilidade');
        const leituraDepoisEl = document.getElementById('leitura-depois-mobilidade');
        const padraoTextoEl = document.getElementById('padrao-utilizado-mobilidade-text');
        const selectPadrao = document.getElementById('selectPadraoUtilizadoMobilidade');
        if (cargaEl && medicao.carga != null) cargaEl.value = parseFloat(medicao.carga).toFixed(3);
        if (sobrecargaEl && medicao.sobrecarga != null) sobrecargaEl.value = parseFloat(medicao.sobrecarga).toFixed(3);
        if (leituraAntesEl && medicao.leitura_antes != null) leituraAntesEl.value = parseFloat(medicao.leitura_antes).toFixed(3);
        if (leituraDepoisEl && medicao.leitura_depois != null) leituraDepoisEl.value = parseFloat(medicao.leitura_depois).toFixed(3);
        if (padraoTextoEl) padraoTextoEl.textContent = medicao.padrao_utilizado || '—';
        if (selectPadrao && medicao.padrao_utilizado_id != null) {
            const idStr = String(medicao.padrao_utilizado_id);
            if (Array.from(selectPadrao.options).some(o => o.value === idStr)) {
                selectPadrao.value = idStr;
            }
        }
        return;
    }
    
    // Mapear pontos baseado no tipo de ensaio (excentricidade / indicação)
    let mapeamentoPontos = {};
    switch (tipoEnsaio) {
        case 'excentricidade':
            mapeamentoPontos = { 1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F', 7: 'G', 8: 'H' };
            break;
        case 'indicacao':
        case 'mobilidade':
            mapeamentoPontos = { 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8' };
            break;
    }
    
    // Verificar quais pontos existem nos pontos dinâmicos
    const pontosExistentes = pesosEnsaiosState.pontosDinamicos.length > 0 
        ? pesosEnsaiosState.pontosDinamicos 
        : [];
    
    // Preencher cada medição
    medicoes.forEach((medicao, idx) => {
        const pontoNumero = medicao.ponto || (idx + 1);
        const pontoLabel = mapeamentoPontos[pontoNumero] || String(pontoNumero);
        
        // Verificar se o ponto existe nos pontos dinâmicos
        if (pontosExistentes.length > 0 && !pontosExistentes.includes(pontoLabel)) {
            return; // Pular este ponto
        }
        
        
        // Preencher carga - verificar existência do elemento antes de acessar
        const cargaEl = document.getElementById(`carga-ponto-${pontoLabel}`);
        if (!cargaEl) {
            return; // Pular este ponto se não existir
        }
        
        // NÃO preencher carga se já houver uma carga atual definida na composição
        // A carga atual da composição tem prioridade sobre a carga salva
        if (pesosEnsaiosState.cargaAtual) {
            // Manter a carga atual (já foi definida por atualizarCargasMedicoes)
        } else if (medicao.carga) {
            // Só preencher carga se não houver carga atual definida
            cargaEl.value = parseFloat(medicao.carga).toFixed(3);
        } else {
        }
        
        // Preencher leituras (verificar múltiplos formatos possíveis)
        const leitura1 = medicao.leitura_1 !== null && medicao.leitura_1 !== undefined ? medicao.leitura_1 : 
                        (medicao.leitura1 !== null && medicao.leitura1 !== undefined ? medicao.leitura1 : null);
        const leitura2 = medicao.leitura_2 !== null && medicao.leitura_2 !== undefined ? medicao.leitura_2 : 
                        (medicao.leitura2 !== null && medicao.leitura2 !== undefined ? medicao.leitura2 : null);
        const leitura3 = medicao.leitura_3 !== null && medicao.leitura_3 !== undefined ? medicao.leitura_3 : 
                        (medicao.leitura3 !== null && medicao.leitura3 !== undefined ? medicao.leitura3 : null);
        const leitura4 = medicao.leitura_4 !== null && medicao.leitura_4 !== undefined ? medicao.leitura_4 : 
                        (medicao.leitura4 !== null && medicao.leitura4 !== undefined ? medicao.leitura4 : null);
        
        if (leitura1 !== null) {
            const leitura1El = document.getElementById(`leitura1-ponto-${pontoLabel}`);
            if (leitura1El) {
                leitura1El.value = parseFloat(leitura1).toFixed(3);
            } else {
            }
        }
        
        if (leitura2 !== null) {
            const leitura2El = document.getElementById(`leitura2-ponto-${pontoLabel}`);
            if (leitura2El) {
                leitura2El.value = parseFloat(leitura2).toFixed(3);
            } else {
            }
        }
        
        if (leitura3 !== null) {
            const leitura3El = document.getElementById(`leitura3-ponto-${pontoLabel}`);
            if (leitura3El) {
                leitura3El.value = parseFloat(leitura3).toFixed(3);
            } else {
            }
        }
        
        if (leitura4 !== null) {
            const leitura4El = document.getElementById(`leitura4-ponto-${pontoLabel}`);
            if (leitura4El) {
                leitura4El.value = parseFloat(leitura4).toFixed(3);
            } else {
            }
        }
    });
    
}

/**
 * Configurar event listeners
 */
function configurarEventListeners() {
    // Select de conjunto
    const selectConjunto = document.getElementById('pesoConjuntoSelect');
    if (selectConjunto) {
        selectConjunto.addEventListener('change', onConjuntoSelecionado);
    }
    
    // Botão carregar itens
    const btnCarregarItens = document.getElementById('btnCarregarItens');
    if (btnCarregarItens) {
        btnCarregarItens.addEventListener('click', () => {
            const certificadoNumero = selectConjunto?.value;
            if (certificadoNumero) {
                carregarItensConjunto(certificadoNumero);
            }
        });
    }
    
    // Input de carga
    const cargaInput = document.getElementById('cargaInput');
    if (cargaInput) {
        // Garantir que o campo não está desabilitado ou readonly
        cargaInput.disabled = false;
        cargaInput.readOnly = false;
        
        // Event listener para input
        cargaInput.addEventListener('input', (e) => {
            const valor = parseFloat(e.target.value) || null;
            definirCarga(valor);
        });
        
        // Event listener para garantir que não seja desabilitado
        cargaInput.addEventListener('focus', () => {
            cargaInput.disabled = false;
            cargaInput.readOnly = false;
        });
        
        // Garantir que o campo esteja acessível quando o accordion for expandido
        const collapseComposicao = document.getElementById('collapseComposicao');
        if (collapseComposicao) {
            collapseComposicao.addEventListener('shown.bs.collapse', () => {
                cargaInput.disabled = false;
                cargaInput.readOnly = false;
                // Reaplicar carga restaurada ao expandir o accordion
                if (pesosEnsaiosState.cargaAtual != null && !Number.isNaN(pesosEnsaiosState.cargaAtual) && !cargaInput.value) {
                    cargaInput.value = Number(pesosEnsaiosState.cargaAtual).toFixed(3);
                }
            });
        }
    }
    
    // Botão compor
    const btnCompor = document.getElementById('btnCompor');
    if (btnCompor) {
        btnCompor.addEventListener('click', comporAutomaticamente);
    }
    
    // Botão ajustar manualmente
    const btnAjustar = document.getElementById('btnAjustar');
    if (btnAjustar) {
        btnAjustar.addEventListener('click', abrirModalAjusteManual);
    }
    
    // Botão aplicar ajuste manual
    const btnAplicarAjuste = document.getElementById('btnAplicarAjusteManual');
    if (btnAplicarAjuste) {
        btnAplicarAjuste.addEventListener('click', aplicarAjusteManual);
    }
    
    // Select tipo de ensaio
    const tipoEnsaioSelect = document.getElementById('tipoEnsaioSelect');
    const blocoMobilidade = document.getElementById('blocoMobilidadePesopadrao');
    if (tipoEnsaioSelect) {
        tipoEnsaioSelect.addEventListener('change', (e) => {
            const tipo = e.target.value;
            if (blocoMobilidade) {
                blocoMobilidade.style.display = tipo === 'mobilidade' ? 'block' : 'none';
            }
            if (tipo === 'mobilidade') {
                carregarCertificadosPESOPADRAO();
            }
            if (tipo) {
                // Inicializar pontos dinâmicos baseado no tipo
                inicializarPontosDinamicos(tipo);
                renderizarMedicoes(tipo);
                
                // Excentricidade/Indicação: se já houver composição, garantir botão "Salvar Ensaio Final" habilitado e tabela visível
                if ((tipo === 'excentricidade' || tipo === 'indicacao') && pesosEnsaiosState.cargaAtual && pesosEnsaiosState.idsSelecionados.length > 0) {
                    renderizarComposicao();
                }
                
                // Após renderizar, atualizar carga atual se houver (não para mobilidade)
                setTimeout(() => {
                    if (tipo !== 'mobilidade' && pesosEnsaiosState.cargaAtual) {
                        atualizarCargasMedicoes(pesosEnsaiosState.cargaAtual);
                    }
                }, 200);
                
                // NÃO carregar medições salvas quando usuário muda manualmente
                // (carregarMedicoesSalvas já restaura o tipo ao abrir modal)
            } else {
                // Limpar tabela se tipo for desmarcado
                const container = document.getElementById('pontosContainer');
                if (container) {
                    container.innerHTML = '';
                }
            }
        });
    }
    
    // Select padrão utilizado (Mobilidade - PESOPADRAO): ao selecionar, preencher Carga, Sobrecarga, Leitura antes/depois
    const selectPadraoMobilidade = document.getElementById('selectPadraoUtilizadoMobilidade');
    if (selectPadraoMobilidade) {
        selectPadraoMobilidade.addEventListener('change', preencherCamposMobilidadeDoPadrao);
    }
    
    // Botão salvar ensaio final
    const btnSalvarFinal = document.getElementById('btnSalvarFinal');
    if (btnSalvarFinal) {
        btnSalvarFinal.addEventListener('click', salvarEnsaioFinal);
    }
}

/**
 * Carregar certificados PESOPADRAO para o select de Mobilidade
 */
async function carregarCertificadosPESOPADRAO() {
    const select = document.getElementById('selectPadraoUtilizadoMobilidade');
    if (!select) return;
    const getCookieFunc = typeof getCookie !== 'undefined' ? getCookie : function(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    };
    const token = getCookieFunc('pdv_automscale_token');
    if (!token) return;
    try {
        const params = new URLSearchParams({ categoria_codigo: 'PESOPADRAO', ativo: 'true', limit: '200' });
        const fetchFn = window.authenticatedFetch || fetch;
        const res = await fetchFn(`/api/v1/aux-cadastros?${params}`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (!res.ok) return;
        const data = await res.json();
        const cadastros = data.cadastros || [];
        select.innerHTML = '<option value="">Selecione o certificado PESOPADRAO</option>';
        cadastros.forEach(c => {
            const att = c.atributos_json || {};
            const cargaKg = att.carga_kg != null ? parseFloat(att.carga_kg) : null;
            const sobrecargaKg = att.sobrecarga_kg != null ? parseFloat(att.sobrecarga_kg) : null;
            const label = (c.nome_titulo || c.certificado_numero || `ID ${c.id}`).trim();
            const opt = document.createElement('option');
            opt.value = String(c.id);
            opt.textContent = label;
            opt.dataset.cargaKg = cargaKg !== null && !Number.isNaN(cargaKg) ? String(cargaKg) : '';
            opt.dataset.sobrecargaKg = sobrecargaKg !== null && !Number.isNaN(sobrecargaKg) ? String(sobrecargaKg) : '';
            opt.dataset.nomeTitulo = c.nome_titulo || '';
            opt.dataset.certificadoNumero = c.certificado_numero || '';
            select.appendChild(opt);
        });
    } catch (e) {
    }
}

/**
 * Preencher campos da tabela Mobilidade a partir do certificado PESOPADRAO selecionado
 * Carga e Sobrecarga vêm do certificado; Leitura antes e Leitura depois = Carga + Sobrecarga
 */
function preencherCamposMobilidadeDoPadrao() {
    const select = document.getElementById('selectPadraoUtilizadoMobilidade');
    if (!select || select.value === '') return;
    const opt = select.options[select.selectedIndex];
    if (!opt) return;
    const cargaKg = parseFloat(opt.dataset.cargaKg) || 0;
    const sobrecargaKg = parseFloat(opt.dataset.sobrecargaKg) || 0;
    const leituraVal = cargaKg + sobrecargaKg;
    const cargaEl = document.getElementById('carga-mobilidade');
    const sobrecargaEl = document.getElementById('sobrecarga-mobilidade');
    const leituraAntesEl = document.getElementById('leitura-antes-mobilidade');
    const leituraDepoisEl = document.getElementById('leitura-depois-mobilidade');
    const padraoTextoEl = document.getElementById('padrao-utilizado-mobilidade-text');
    const label = (opt.dataset.nomeTitulo || opt.dataset.certificadoNumero || opt.textContent || '—').trim();
    if (cargaEl) cargaEl.value = cargaKg.toFixed(3);
    if (sobrecargaEl) sobrecargaEl.value = sobrecargaKg.toFixed(3);
    if (leituraAntesEl) leituraAntesEl.value = leituraVal.toFixed(3);
    if (leituraDepoisEl) leituraDepoisEl.value = leituraVal.toFixed(3);
    if (padraoTextoEl) padraoTextoEl.textContent = label || '—';
}

/**
 * Carregar conjuntos de pesos padrão
 */
async function carregarConjuntos() {
    const select = document.getElementById('pesoConjuntoSelect');
    if (!select) {
        return;
    }
    
    select.innerHTML = '<option value="">Carregando conjuntos...</option>';
    select.disabled = true;
    
    try {
        // Usar getCookie do escopo global ou função auxiliar
        const getCookieFunc = typeof getCookie !== 'undefined' ? getCookie : function(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        };
        
        const token = getCookieFunc('pdv_automscale_token');
        if (!token) {
            throw new Error('Token de autenticação não encontrado. Faça login novamente.');
        }
        
        const fetchFn = window.authenticatedFetch || fetch;
        const response = await fetchFn('/api/v1/aux-cadastros/pesos/conjuntos', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Erro HTTP: ${response.status} - ${errorText}`);
        }
        
        // A API retorna uma lista diretamente, não um objeto com 'conjuntos'
        const conjuntos = await response.json();
        
        
        // Verificar se é array ou objeto com propriedade conjuntos
        const conjuntosList = Array.isArray(conjuntos) ? conjuntos : (conjuntos.conjuntos || []);
        
        select.innerHTML = '<option value="">Selecione um conjunto...</option>';
        
        if (conjuntosList.length === 0) {
            select.innerHTML = '<option value="">Nenhum conjunto encontrado</option>';
            return;
        }
        
        conjuntosList.forEach(conjunto => {
            const option = document.createElement('option');
            option.value = conjunto.certificado_numero;
            const somaMax = typeof conjunto.soma_maxima === 'number' ? conjunto.soma_maxima.toFixed(3) : conjunto.soma_maxima || '0';
            option.textContent = `${conjunto.certificado_numero} - ${conjunto.quantidade_pecas} peças - Soma máx: ${somaMax} kg`;
            option.dataset.conjunto = JSON.stringify(conjunto);
            select.appendChild(option);
        });
        
        select.disabled = false;
        
        // Se houver conjunto salvo, selecionar automaticamente
        if (pesosEnsaiosState.conjuntoSalvo && !pesosEnsaiosState.conjuntoSalvoAplicado) {
            const optionExists = Array.from(select.options || []).some(opt => opt.value === pesosEnsaiosState.conjuntoSalvo);
            if (optionExists) {
                select.value = pesosEnsaiosState.conjuntoSalvo;
                onConjuntoSelecionado();
                // Reaplicar composição salva após onConjuntoSelecionado limpar estado
                pesosEnsaiosState.cargaAtual = pesosEnsaiosState.composicaoSalva?.carga ?? null;
                pesosEnsaiosState.idsSelecionados = Array.isArray(pesosEnsaiosState.composicaoSalva?.ids) ? pesosEnsaiosState.composicaoSalva.ids : [];
                pesosEnsaiosState.resumoSelecionado = Array.isArray(pesosEnsaiosState.composicaoSalva?.resumo) ? pesosEnsaiosState.composicaoSalva.resumo : [];
                renderizarComposicao();
                carregarItensConjunto(pesosEnsaiosState.conjuntoSalvo);
                pesosEnsaiosState.conjuntoSalvoAplicado = true;
            }
        }
        
    } catch (error) {
        select.innerHTML = '<option value="">Erro ao carregar conjuntos</option>';
        mostrarAlerta('Erro ao carregar conjuntos: ' + error.message, 'danger');
    }
}

/**
 * Handler quando conjunto é selecionado
 */
function onConjuntoSelecionado() {
    const select = document.getElementById('pesoConjuntoSelect');
    if (!select || !select.value) {
        return;
    }
    
    const conjuntoData = JSON.parse(select.options[select.selectedIndex].dataset.conjunto || '{}');
    pesosEnsaiosState.conjunto = conjuntoData;
    
    // Limpar itens e composição
    pesosEnsaiosState.itens = [];
    pesosEnsaiosState.idsSelecionados = [];
    pesosEnsaiosState.resumoSelecionado = [];
    
    // Habilitar botão carregar itens
    const btnCarregarItens = document.getElementById('btnCarregarItens');
    if (btnCarregarItens) {
        btnCarregarItens.disabled = false;
    }
    
    // Atualizar resumo do conjunto
    atualizarResumoConjunto(conjuntoData);
    
    // Limpar composição
    renderizarComposicao();
    
}

/**
 * Atualizar resumo do conjunto (badges)
 */
function atualizarResumoConjunto(conjunto) {
    const container = document.getElementById('pesoConjuntoResumo');
    if (!container) return;
    
    if (!conjunto) {
        container.innerHTML = '';
        return;
    }
    
    const badges = [];
    
    // Número do certificado (sempre exibir)
    if (conjunto.certificado_numero) {
        badges.push(`<span class="badge bg-primary">Certificado: ${conjunto.certificado_numero}</span>`);
    }
    
    if (conjunto.validade_min) {
        // Formatar data se for string ISO
        let validadeFormatada = conjunto.validade_min;
        if (typeof validadeFormatada === 'string' && validadeFormatada.includes('T')) {
            validadeFormatada = validadeFormatada.split('T')[0];
        }
        badges.push(`<span class="badge bg-success">Validade mín: ${validadeFormatada}</span>`);
    }
    
    if (conjunto.quantidade_pecas) {
        badges.push(`<span class="badge bg-info">${conjunto.quantidade_pecas} peças</span>`);
    }
    
    if (conjunto.classe) {
        badges.push(`<span class="badge bg-secondary">Classe: ${conjunto.classe}</span>`);
    }
    
    if (conjunto.soma_maxima) {
        const somaMax = typeof conjunto.soma_maxima === 'number' ? conjunto.soma_maxima.toFixed(3) : conjunto.soma_maxima;
        badges.push(`<span class="badge bg-warning text-dark">Soma máx: ${somaMax} kg</span>`);
    }
    
    container.innerHTML = badges.join(' ');
}

/**
 * Carregar itens (peças) do conjunto
 */
async function carregarItensConjunto(certificadoNumero) {
    const listaItens = document.getElementById('pesoItensList');
    if (!listaItens) return;
    
    listaItens.innerHTML = '<div class="text-center text-muted py-3">Carregando peças...</div>';
    
    try {
        // Usar getCookie do escopo global ou função auxiliar
        const getCookieFunc = typeof getCookie !== 'undefined' ? getCookie : function(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        };
        
        const token = getCookieFunc('pdv_automscale_token');
        if (!token) {
            throw new Error('Token de autenticação não encontrado. Faça login novamente.');
        }
        
        const fetchFn = window.authenticatedFetch || fetch;
        const response = await fetchFn(`/api/v1/aux-cadastros/pesos/itens?certificado_numero=${encodeURIComponent(certificadoNumero)}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        
        // A API retorna uma lista diretamente, não um objeto com 'itens'
        const data = await response.json();
        const itens = Array.isArray(data) ? data : (data.itens || []);
        
        pesosEnsaiosState.itens = itens;
        
        if (itens.length === 0) {
            listaItens.innerHTML = '<div class="text-center text-muted py-3">Nenhuma peça encontrada</div>';
            return;
        }
        
        // Renderizar lista de peças
        // A API retorna objetos com valor_nominal, unidade, classe diretamente (não em atributos_json)
        listaItens.innerHTML = itens.map(item => {
            // Tentar atributos_json primeiro, depois campos diretos
            const atributos = item.atributos_json || {};
            const valorNominal = item.valor_nominal || atributos.valor_nominal || 'N/A';
            const unidade = item.unidade || atributos.unidade || 'kg';
            const classe = item.classe || atributos.classe || 'N/A';
            const identificador = item.identificador || `ID ${item.id}`;
            
            // Formatar valor_nominal se for Decimal/Number
            const valorFormatado = typeof valorNominal === 'number' ? valorNominal.toFixed(3) : valorNominal;
            
            return `
                <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                    <div>
                        <strong>${identificador}</strong>
                        <small class="d-block text-muted">${valorFormatado} ${unidade} - Classe: ${classe}</small>
                    </div>
                    <span class="badge bg-secondary">ID: ${item.id}</span>
                </div>
            `;
        }).join('');
        
        // Vincular conjunto à balança automaticamente
        await vincularConjuntoBalanca(certificadoNumero);
        
        // Habilitar composição
        const btnCompor = document.getElementById('btnCompor');
        const btnAjustar = document.getElementById('btnAjustar');
        if (btnCompor) btnCompor.disabled = false;
        if (btnAjustar) btnAjustar.disabled = false;
        
        
    } catch (error) {
        listaItens.innerHTML = '<div class="text-center text-danger py-3">Erro ao carregar peças</div>';
        mostrarAlerta('Erro ao carregar peças: ' + error.message, 'danger');
    }
}

/**
 * Vincular conjunto à balança (papel=peso_padrao)
 */
async function vincularConjuntoBalanca(certificadoNumero) {
    if (!pesosEnsaiosState.processoId || !pesosEnsaiosState.balancaId || !pesosEnsaiosState.itens.length) {
        return;
    }
    
    try {
        // Usar getCookie do escopo global ou função auxiliar
        const getCookieFunc = typeof getCookie !== 'undefined' ? getCookie : function(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        };
        
        const token = getCookieFunc('pdv_automscale_token');
        if (!token) {
            return;
        }
        
        for (let idx = 0; idx < pesosEnsaiosState.itens.length; idx++) {
            const peca = pesosEnsaiosState.itens[idx];
            const fetchFn = window.authenticatedFetch || fetch;
            const response = await fetchFn(`/api/v1/processos/${pesosEnsaiosState.processoId}/balancas/${pesosEnsaiosState.balancaId}/aux-cadastros`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    aux_cadastro_id: peca.id,
                    papel: 'peso_padrao',
                    ordem: idx + 1
                })
            });
            
            if (response.ok) {
                continue;
            }
            
            const errorText = await response.text();
            let errorDetail = 'Erro desconhecido';
            try {
                const error = JSON.parse(errorText);
                errorDetail = error.detail || error.message || errorText;
            } catch (e) {
                errorDetail = errorText || `Erro HTTP ${response.status}`;
            }
        }
    } catch (error) {
    }
}

/**
 * Definir carga atual
 */
function definirCarga(valor) {
    pesosEnsaiosState.cargaAtual = valor;
    
    // Atualizar campo de input
    const cargaInput = document.getElementById('cargaInput');
    if (cargaInput) {
        // Garantir que o campo não está desabilitado
        cargaInput.disabled = false;
        cargaInput.readOnly = false;
        cargaInput.value = valor ? valor.toFixed(3) : '';
    }
    
    // Atualizar campos de carga na tabela de medições (autocompletar)
    atualizarCargasMedicoes(valor);
    
    // Atualizar botões de composição
    const btnCompor = document.getElementById('btnCompor');
    const btnAjustar = document.getElementById('btnAjustar');
    
    const podeCompor = valor && valor > 0 && pesosEnsaiosState.itens.length > 0;
    
    if (btnCompor) btnCompor.disabled = !podeCompor;
    if (btnAjustar) btnAjustar.disabled = !podeCompor;
    
}

/**
 * Atualizar campos de carga na tabela de medições (autocompletar)
 */
function atualizarCargasMedicoes(valor) {
    if (!valor || valor <= 0) return;
    
    // Verificar qual tipo de ensaio está selecionado
    const tipoEnsaioSelect = document.getElementById('tipoEnsaioSelect');
    const tipoEnsaio = tipoEnsaioSelect?.value;
    
    if (!tipoEnsaio) return;
    
        // Usar pontos dinâmicos ou determinar baseado no tipo de ensaio
        let pontos = pesosEnsaiosState.pontosDinamicos.length > 0 
            ? pesosEnsaiosState.pontosDinamicos 
            : [];
        
        if (pontos.length === 0) {
            switch (tipoEnsaio) {
                case 'excentricidade':
                    pontos = ['A', 'B', 'C'];
                    break;
                case 'indicacao':
                    pontos = ['1', '2'];
                    break;
                case 'mobilidade':
                    pontos = ['1'];
                    break;
                default:
                    return;
            }
        }
    
    const valorStr = valor.toFixed(3);
    // Excentricidade/Indicação: autopreencher Leitura 1,2,3,4 com o valor da Carga (coluna 2), editáveis
    if (tipoEnsaio === 'excentricidade' || tipoEnsaio === 'indicacao') {
        pontos.forEach(ponto => {
            const cargaEl = document.getElementById(`carga-ponto-${ponto}`);
            if (cargaEl) cargaEl.value = valorStr;
            const leitura1El = document.getElementById(`leitura1-ponto-${ponto}`);
            const leitura2El = document.getElementById(`leitura2-ponto-${ponto}`);
            const leitura3El = document.getElementById(`leitura3-ponto-${ponto}`);
            const leitura4El = document.getElementById(`leitura4-ponto-${ponto}`);
            if (leitura1El) leitura1El.value = valorStr;
            if (leitura2El) leitura2El.value = valorStr;
            if (leitura3El) leitura3El.value = valorStr;
            if (leitura4El) leitura4El.value = valorStr;
        });
    } else {
        pontos.forEach(ponto => {
            const cargaEl = document.getElementById(`carga-ponto-${ponto}`);
            if (cargaEl) cargaEl.value = valorStr;
        });
    }
    
}

/**
 * Salvar composição atual (carga + peças) no backend (etapa 2), para restaurar ao reabrir o modal.
 */
async function salvarComposicaoAtual() {
    if (!pesosEnsaiosState.processoId || !pesosEnsaiosState.balancaId) return;
    const carga = pesosEnsaiosState.cargaAtual;
    if (carga == null || carga === undefined || Number.isNaN(parseFloat(carga))) return;
    const getCookieFunc = typeof getCookie !== 'undefined' ? getCookie : function(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    };
    const token = getCookieFunc('pdv_automscale_token');
    if (!token) return;
    const certificadoNumero = pesosEnsaiosState.conjunto?.certificado_numero || pesosEnsaiosState.conjuntoSalvo || null;
    const pesosIds = pesosEnsaiosState.idsSelecionados || [];
    const pesosResumo = pesosEnsaiosState.resumoSelecionado || null;
    try {
        const fetchFn = window.authenticatedFetch || fetch;
        const res = await fetchFn(
            `/api/v1/processos/${pesosEnsaiosState.processoId}/balancas/${pesosEnsaiosState.balancaId}/composicao-pesos`,
            {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    carga: carga,
                    certificado_numero: certificadoNumero,
                    pesos_ids: pesosIds,
                    pesos_resumo: pesosResumo
                })
            }
        );
        if (res.ok) {
        } else {
        }
    } catch (e) {
    }
}

/**
 * Compor automaticamente (greedy + backtracking curto)
 */
async function comporAutomaticamente() {
    if (!pesosEnsaiosState.cargaAtual || !pesosEnsaiosState.itens.length || !pesosEnsaiosState.conjunto) {
        mostrarAlerta('Selecione um conjunto, carregue as peças e defina a carga', 'warning');
        return;
    }
    
    const btnCompor = document.getElementById('btnCompor');
    if (btnCompor) {
        btnCompor.disabled = true;
        btnCompor.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Compondo...';
    }
    
    try {
        // Usar getCookie do escopo global ou função auxiliar
        const getCookieFunc = typeof getCookie !== 'undefined' ? getCookie : function(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        };
        
        const token = getCookieFunc('pdv_automscale_token');
        if (!token) {
            throw new Error('Token de autenticação não encontrado. Faça login novamente.');
        }
        
        const fetchFn = window.authenticatedFetch || fetch;
        const response = await fetchFn('/api/v1/aux-cadastros/pesos/compor', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                certificado_numero: pesosEnsaiosState.conjunto.certificado_numero,
                carga: pesosEnsaiosState.cargaAtual
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao compor pesos');
        }
        
        const data = await response.json();
        
        // A API retorna ids_selecionados e detalhes
        if (data.ids_selecionados && data.ids_selecionados.length > 0) {
            pesosEnsaiosState.idsSelecionados = data.ids_selecionados;
            pesosEnsaiosState.resumoSelecionado = data.detalhes || [];
            
            renderizarComposicao();
            
            // Se já houver tipo de ensaio selecionado, renderizar/atualizar tabela de medições
            const tipoEnsaioSelect = document.getElementById('tipoEnsaioSelect');
            const tipoEnsaio = tipoEnsaioSelect?.value;
            
            if (tipoEnsaio) {
                // Se pontos dinâmicos não foram inicializados, inicializar agora
                if (pesosEnsaiosState.pontosDinamicos.length === 0) {
                    inicializarPontosDinamicos(tipoEnsaio);
                }
                // Renderizar tabela de medições
                renderizarMedicoes(tipoEnsaio);
                
                // Garantir que carga seja atualizada após renderização
                setTimeout(() => {
                    if (pesosEnsaiosState.cargaAtual) {
                        atualizarCargasMedicoes(pesosEnsaiosState.cargaAtual);
                    }
                }, 250);
            } else {
            }
            
            mostrarAlerta(`✅ Composição automática realizada: ${data.ids_selecionados.length} peça(s) selecionada(s)`, 'success');
            await salvarComposicaoAtual();
        } else {
            mostrarAlerta('Não foi possível encontrar uma composição para esta carga. Tente ajustar manualmente.', 'warning');
        }
        
    } catch (error) {
        mostrarAlerta('Erro ao compor automaticamente: ' + error.message, 'danger');
    } finally {
        if (btnCompor) {
            btnCompor.disabled = false;
            btnCompor.innerHTML = '<i data-feather="cpu" class="me-2" style="width: 14px; height: 14px;"></i>Compor Automaticamente';
            // Aguardar um pouco antes de chamar feather.replace() para garantir que o DOM foi atualizado
            setTimeout(() => {
                if (typeof atualizarFeatherIcons === 'function') {
                    atualizarFeatherIcons();
                } else if (typeof feather !== 'undefined' && feather.replace) {
                    try {
                        feather.replace();
                    } catch (e) {
                    }
                }
            }, 50);
        }
    }
}

/**
 * Renderizar composição atual (chips e soma)
 */
function renderizarComposicao() {
    const container = document.getElementById('composicaoAtual');
    const somaContainer = document.getElementById('composicaoSoma');
    
    if (!container || !somaContainer) return;
    
    if (pesosEnsaiosState.idsSelecionados.length === 0) {
        container.innerHTML = '<span class="badge bg-secondary">Nenhuma composição</span>';
        somaContainer.textContent = 'Soma: 0.000 kg';
        return;
    }
    
    // Renderizar chips
    const chips = pesosEnsaiosState.resumoSelecionado.map(item => {
        return `<span class="badge bg-primary me-1">ID ${item.id}: ${item.valor_nominal} ${item.unidade}</span>`;
    }).join('');
    
    container.innerHTML = chips || pesosEnsaiosState.idsSelecionados.map(id => {
        return `<span class="badge bg-primary me-1">ID ${id}</span>`;
    }).join('');
    
    // Calcular e exibir soma
    const soma = pesosEnsaiosState.resumoSelecionado.reduce((acc, item) => {
        return acc + parseFloat(item.valor_nominal || 0);
    }, 0);
    
    const carga = pesosEnsaiosState.cargaAtual || 0;
    const diferenca = Math.abs(soma - carga);
    const ok = diferenca <= TOLERANCIA_SOMA;
    
    somaContainer.innerHTML = `
        <strong>Soma:</strong> ${soma.toFixed(3)} kg
        ${pesosEnsaiosState.cargaAtual ? `<br><strong>Carga:</strong> ${carga.toFixed(3)} kg` : ''}
        ${pesosEnsaiosState.cargaAtual ? `<br><span class="${ok ? 'text-success' : 'text-danger'}">${ok ? '✓ OK' : '⚠ Diferença: ' + diferenca.toFixed(3) + ' kg'}</span>` : ''}
    `;
    
    // Habilitar botão "Salvar Ensaio Final" quando houver carga e pelo menos uma peça na composição
    // (não exige ok da soma para permitir salvar; a exibição ✓/⚠ segue usando ok)
    const btnSalvarFinal = document.getElementById('btnSalvarFinal');
    const podeSalvar = pesosEnsaiosState.cargaAtual && pesosEnsaiosState.idsSelecionados.length > 0;
    
    if (btnSalvarFinal) btnSalvarFinal.disabled = !podeSalvar;
    
    const tipoEnsaioSelect = document.getElementById('tipoEnsaioSelect');
    const tipoEnsaio = tipoEnsaioSelect?.value;
    // Excentricidade/Indicação: se o usuário já tinha selecionado o tipo antes de compor, a tabela
    // não foi construída (renderizarMedicoes retorna cedo). Re-renderizar agora para exibir a tabela.
    if (podeSalvar && tipoEnsaio && (tipoEnsaio === 'excentricidade' || tipoEnsaio === 'indicacao')) {
        renderizarMedicoes(tipoEnsaio);
    } else if (tipoEnsaio && pesosEnsaiosState.cargaAtual) {
        // Atualizar campos de carga na tabela se já existir
        atualizarCargasMedicoes(pesosEnsaiosState.cargaAtual);
    }
}

/**
 * Abrir modal de ajuste manual
 */
function abrirModalAjusteManual() {
    if (!pesosEnsaiosState.itens.length || !pesosEnsaiosState.cargaAtual) {
        mostrarAlerta('Carregue as peças e defina a carga primeiro', 'warning');
        return;
    }
    
    const modal = document.getElementById('modalAjusteManualPesosCustom');
    if (!modal) {
        return;
    }
    
    const listaPecas = document.getElementById('listaPecasAjusteManual');
    const cargaDesejada = document.getElementById('cargaDesejadaModal');
    
    if (cargaDesejada) {
        cargaDesejada.textContent = pesosEnsaiosState.cargaAtual.toFixed(3);
    }
    
    // Renderizar checkboxes
    if (listaPecas) {
        listaPecas.innerHTML = pesosEnsaiosState.itens.map(item => {
            // Tentar atributos_json primeiro, depois campos diretos
            const atributos = item.atributos_json || {};
            const valorNominal = item.valor_nominal || atributos.valor_nominal || 0;
            const unidade = item.unidade || atributos.unidade || 'kg';
            const classe = item.classe || atributos.classe || 'N/A';
            const identificador = item.identificador || `ID ${item.id}`;
            const checked = pesosEnsaiosState.idsSelecionados.includes(item.id) ? 'checked' : '';
            
            // Converter para número se necessário
            const valorNum = typeof valorNominal === 'string' ? parseFloat(valorNominal) : (typeof valorNominal === 'number' ? valorNominal : 0);
            const valorFormatado = valorNum.toFixed(3);
            
            return `
                <div style="padding: 0.5rem; border-bottom: 1px solid #e9ecef; transition: background-color 0.2s ease;" onmouseover="this.style.backgroundColor='#f8f9fa'" onmouseout="this.style.backgroundColor='transparent'">
                    <label style="display: flex; align-items: center; cursor: pointer; margin: 0;">
                        <input type="checkbox" value="${item.id}" id="peca-${item.id}" 
                            data-valor-nominal="${valorNum}" ${checked} onchange="atualizarSomaModal()" 
                            style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                        <span>
                            <strong>${identificador}</strong> - ${valorFormatado} ${unidade} (Classe: ${classe})
                        </span>
                    </label>
                </div>
            `;
        }).join('');
    }
    
    // Atualizar soma inicial
    atualizarSomaModal();
    
    // Abrir modal usando padrão customizado
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    // Atualizar ícones Feather
    if (typeof atualizarFeatherIcons === 'function') {
        atualizarFeatherIcons();
    } else if (typeof feather !== 'undefined' && feather.replace) {
        setTimeout(() => {
            try {
                feather.replace();
            } catch (e) {
            }
        }, 50);
    }
}

/**
 * Fechar modal de ajuste manual
 */
function fecharModalAjusteManualPesos() {
    const modal = document.getElementById('modalAjusteManualPesosCustom');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

/**
 * Atualizar soma no modal de ajuste manual
 */
function atualizarSomaModal() {
    const checkboxes = document.querySelectorAll('#listaPecasAjusteManual input[type="checkbox"]:checked');
    const somaAtual = document.getElementById('somaAtualModal');
    const statusSoma = document.getElementById('statusSomaModal');
    
    if (!somaAtual || !statusSoma) return;
    
    let soma = 0;
    checkboxes.forEach(cb => {
        const valor = parseFloat(cb.dataset.valorNominal || 0);
        soma += valor;
    });
    
    somaAtual.textContent = soma.toFixed(3);
    
    const carga = pesosEnsaiosState.cargaAtual || 0;
    const diferenca = Math.abs(soma - carga);
    const ok = diferenca <= TOLERANCIA_SOMA;
    
    if (ok) {
        statusSoma.textContent = '✓ Soma está dentro da tolerância';
        statusSoma.className = 'text-success';
    } else {
        statusSoma.textContent = `⚠ Diferença: ${diferenca.toFixed(3)} kg (tolerância: ${TOLERANCIA_SOMA} kg)`;
        statusSoma.className = 'text-warning';
    }
}

/**
 * Aplicar ajuste manual
 */
function aplicarAjusteManual() {
    const checkboxes = document.querySelectorAll('#listaPecasAjusteManual input[type="checkbox"]:checked');
    
    const idsSelecionados = Array.from(checkboxes).map(cb => parseInt(cb.value));
    
    if (idsSelecionados.length === 0) {
        mostrarAlerta('Selecione pelo menos uma peça', 'warning');
        return;
    }
    
    // Calcular soma
    let soma = 0;
    const resumo = [];
    
        checkboxes.forEach(cb => {
            const id = parseInt(cb.value);
            const valorNominal = parseFloat(cb.dataset.valorNominal || 0);
            soma += valorNominal;
            
            // Buscar item completo
            const item = pesosEnsaiosState.itens.find(i => i.id === id);
            if (item) {
                // Tentar atributos_json primeiro, depois campos diretos
                const atributos = item.atributos_json || {};
                resumo.push({
                    id: item.id,
                    valor_nominal: valorNominal,
                    unidade: item.unidade || atributos.unidade || 'kg',
                    classe: item.classe || atributos.classe || 'N/A',
                    identificador: item.identificador || `ID ${item.id}`
                });
            }
        });
    
    const carga = pesosEnsaiosState.cargaAtual || 0;
    const diferenca = Math.abs(soma - carga);
    
    if (diferenca > TOLERANCIA_SOMA) {
        if (!confirm(`A soma (${soma.toFixed(3)} kg) difere da carga (${carga.toFixed(3)} kg) em ${diferenca.toFixed(3)} kg. Deseja continuar mesmo assim?`)) {
            return;
        }
    }
    
    pesosEnsaiosState.idsSelecionados = idsSelecionados;
    pesosEnsaiosState.resumoSelecionado = resumo;
    
    renderizarComposicao();
    salvarComposicaoAtual();
    
    // Fechar modal usando padrão customizado
    fecharModalAjusteManualPesos();
    
}

/**
 * Inicializar pontos dinâmicos baseado no tipo de ensaio
 */
function inicializarPontosDinamicos(tipoEnsaio) {
    switch (tipoEnsaio) {
        case 'excentricidade':
            // Excentricidade: começar com A, B (padrão), mas permitir adicionar mais
            pesosEnsaiosState.pontosDinamicos = ['A', 'B'];
            break;
        case 'indicacao':
            // Indicação: começar com 2 pontos por padrão
            pesosEnsaiosState.pontosDinamicos = ['1', '2'];
            break;
        case 'mobilidade':
            // Mobilidade: começar com 1 ponto (padrão), mas permitir adicionar mais
            pesosEnsaiosState.pontosDinamicos = ['1'];
            break;
        default:
            pesosEnsaiosState.pontosDinamicos = [];
    }
}

/**
 * Adicionar novo ponto dinamicamente
 */
function adicionarPonto() {
    const tipoEnsaioSelect = document.getElementById('tipoEnsaioSelect');
    const tipoEnsaio = tipoEnsaioSelect?.value;
    
    if (!tipoEnsaio) {
        return;
    }
    
    let novoPonto = null;
    
    switch (tipoEnsaio) {
        case 'indicacao':
        case 'mobilidade': {
            // Para indicação e mobilidade: adicionar próximo número (1, 2, 3, 4...)
            if (pesosEnsaiosState.pontosDinamicos.length === 0) {
                inicializarPontosDinamicos(tipoEnsaio);
                return;
            }
            const ultimoPonto = pesosEnsaiosState.pontosDinamicos[pesosEnsaiosState.pontosDinamicos.length - 1];
            const proximoNumero = parseInt(ultimoPonto, 10) + 1;
            if (Number.isNaN(proximoNumero)) return;
            novoPonto = String(proximoNumero);
            break;
        }
        case 'excentricidade': {
            // Para excentricidade: adicionar próxima letra (A, B, C, D, E...)
            if (pesosEnsaiosState.pontosDinamicos.length === 0) {
                inicializarPontosDinamicos('excentricidade');
                return;
            }
            const ultimoPontoExcentricidade = pesosEnsaiosState.pontosDinamicos[pesosEnsaiosState.pontosDinamicos.length - 1];
            if (ultimoPontoExcentricidade == null || typeof ultimoPontoExcentricidade !== 'string') return;
            const proximaLetra = String.fromCharCode(ultimoPontoExcentricidade.charCodeAt(0) + 1);
            novoPonto = proximaLetra;
            break;
        }
        default:
            return;
    }
    
    if (novoPonto) {
        pesosEnsaiosState.pontosDinamicos.push(novoPonto);
        // Re-renderizar medições
        renderizarMedicoes(tipoEnsaio);
    }
}

/**
 * Remover ponto dinamicamente
 */
function removerPonto(ponto) {
    const tipoEnsaioSelect = document.getElementById('tipoEnsaioSelect');
    const tipoEnsaio = tipoEnsaioSelect?.value;
    
    if (!tipoEnsaio) {
        return;
    }
    
    // Determinar mínimo de pontos por tipo
    let minimoPontos = 1;
    switch (tipoEnsaio) {
        case 'indicacao':
            minimoPontos = 2; // Indicação: mínimo 2 pontos
            break;
        case 'excentricidade':
            minimoPontos = 2; // Excentricidade: mínimo 2 pontos (A, B)
            break;
        case 'mobilidade':
            minimoPontos = 1; // Mobilidade: mínimo 1 ponto
            break;
    }
    
    // Não permitir remover se tiver menos que o mínimo
    if (pesosEnsaiosState.pontosDinamicos.length <= minimoPontos) {
        mostrarAlerta(`É necessário manter pelo menos ${minimoPontos} ponto(s) para este tipo de ensaio`, 'warning');
        return;
    }
    
    // Remover ponto
    pesosEnsaiosState.pontosDinamicos = pesosEnsaiosState.pontosDinamicos.filter(p => p !== ponto);
    
    // Re-renderizar medições
    renderizarMedicoes(tipoEnsaio);
}

/**
 * Renderizar medições baseado no tipo de ensaio
 * Excentricidade e Indicação: sem alteração (tabela com Ponto, Carga, Leitura 1-4).
 * Mobilidade: tabela específica (Carga, Sobrecarga, Leitura antes, Leitura depois, Padrão utilizado).
 */
function renderizarMedicoes(tipoEnsaio) {
    const container = document.getElementById('pontosContainer');
    if (!container) return;
    
    if (tipoEnsaio === 'mobilidade') {
        // Mobilidade: uma linha, 5 colunas (Carga, Sobrecarga, Leitura antes, Leitura depois, Padrão utilizado). Sem Ponto, sem Leitura 4.
        const cargaVal = document.getElementById('carga-mobilidade')?.value || '';
        const sobrecargaVal = document.getElementById('sobrecarga-mobilidade')?.value || '';
        const leituraAntesVal = document.getElementById('leitura-antes-mobilidade')?.value || '';
        const leituraDepoisVal = document.getElementById('leitura-depois-mobilidade')?.value || '';
        const padraoTexto = document.getElementById('padrao-utilizado-mobilidade-text');
        const padraoVal = padraoTexto ? padraoTexto.textContent : '';
        container.innerHTML = `
        <table class="table table-bordered table-sm">
            <thead>
                <tr>
                    <th>Carga (kg)</th>
                    <th>Sobrecarga (kg)</th>
                    <th>Leitura antes (kg)</th>
                    <th>Leitura depois (kg)</th>
                    <th>Padrão utilizado</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><input type="number" class="form-control form-control-sm" id="carga-mobilidade" step="0.001" placeholder="0.000" value="${cargaVal}"></td>
                    <td><input type="number" class="form-control form-control-sm" id="sobrecarga-mobilidade" step="0.001" placeholder="0.000" value="${sobrecargaVal}"></td>
                    <td><input type="number" class="form-control form-control-sm" id="leitura-antes-mobilidade" step="0.001" placeholder="0.000" value="${leituraAntesVal}"></td>
                    <td><input type="number" class="form-control form-control-sm" id="leitura-depois-mobilidade" step="0.001" placeholder="0.000" value="${leituraDepoisVal}"></td>
                    <td><span id="padrao-utilizado-mobilidade-text" class="text-muted">${padraoVal || '—'}</span></td>
                </tr>
            </tbody>
        </table>`;
        return;
    }
    
    if (!pesosEnsaiosState.cargaAtual || pesosEnsaiosState.idsSelecionados.length === 0) {
        container.innerHTML = '<div class="alert alert-warning">Defina a carga e a composição primeiro</div>';
        return;
    }
    
    // Se pontos dinâmicos não foram inicializados, inicializar agora
    if (pesosEnsaiosState.pontosDinamicos.length === 0) {
        inicializarPontosDinamicos(tipoEnsaio);
    }
    
    const pontos = pesosEnsaiosState.pontosDinamicos;
    
    if (pontos.length === 0) {
        container.innerHTML = '<div class="alert alert-warning">Tipo de ensaio inválido</div>';
        return;
    }
    
    // Determinar se pode adicionar/remover pontos (agora para todos os tipos)
    const podeAdicionar = true; // Todos os tipos podem adicionar pontos
    let podeRemover = false;
    let minimoPontos = 1;
    
    switch (tipoEnsaio) {
        case 'indicacao':
            minimoPontos = 2;
            podeRemover = pontos.length > minimoPontos;
            break;
        case 'excentricidade':
            minimoPontos = 2;
            podeRemover = pontos.length > minimoPontos;
            break;
        case 'mobilidade':
            minimoPontos = 1;
            podeRemover = pontos.length > minimoPontos;
            break;
    }
    
    // Para indicação: exibir fator k e coluna incerteza (ISO 17025)
    const exibeIncerteza = (tipoEnsaio === 'indicacao' || tipoEnsaio === 'excentricidade');
    const fatorKDefault = '2';
    
    // Criar tabela responsiva
    const tabela = `
        <div class="mb-2 d-flex justify-content-between align-items-center flex-wrap gap-2">
            <span class="text-muted small">Pontos de medição</span>
            ${exibeIncerteza ? `
                <div class="d-flex align-items-center gap-2">
                    <label class="small mb-0" for="fator-abrangencia-global" title="Fator de abrangência k (95% de confiança)">
                        k = 
                    </label>
                    <input type="number" class="form-control form-control-sm" id="fator-abrangencia-global" 
                        value="${fatorKDefault}" step="0.01" min="1" max="3" style="width: 60px;" 
                        title="Fator de abrangência (ex: 2 = 95%)">
                </div>
            ` : ''}
            ${podeAdicionar ? `
                <button type="button" class="btn btn-sm btn-outline-success" onclick="adicionarPonto()" title="Adicionar ponto">
                    <i data-feather="plus" style="width: 14px; height: 14px;"></i> Adicionar Ponto
                </button>
            ` : ''}
        </div>
        <table class="table table-bordered table-sm">
            <thead>
                <tr>
                    <th>Ponto</th>
                    <th>Carga (kg)</th>
                    <th>Leitura 1</th>
                    <th>Leitura 2</th>
                    <th>Leitura 3</th>
                    <th>Leitura 4</th>
                    ${exibeIncerteza ? '<th>Incerteza (kg)</th>' : ''}
                    ${podeRemover ? '<th style="width: 50px;">Ação</th>' : ''}
                </tr>
            </thead>
            <tbody>
                ${pontos.map(ponto => {
                    const cargaValue = pesosEnsaiosState.cargaAtual ? pesosEnsaiosState.cargaAtual.toFixed(3) : '0.000';
                    const leitura1Val = cargaValue;
                    const leitura2Val = cargaValue;
                    const leitura3Val = cargaValue;
                    const leitura4Val = cargaValue;
                    return `
                    <tr id="linha-ponto-${ponto}">
                        <td><strong>${ponto}</strong></td>
                        <td>
                            <input type="number" class="form-control form-control-sm" 
                                id="carga-ponto-${ponto}" 
                                value="${cargaValue}" 
                                step="0.001" readonly>
                        </td>
                        <td>
                            <input type="number" class="form-control form-control-sm" 
                                id="leitura1-ponto-${ponto}" 
                                step="0.001" placeholder="0.000" value="${leitura1Val}">
                        </td>
                        <td>
                            <input type="number" class="form-control form-control-sm" 
                                id="leitura2-ponto-${ponto}" 
                                step="0.001" placeholder="0.000" value="${leitura2Val}">
                        </td>
                        <td>
                            <input type="number" class="form-control form-control-sm" 
                                id="leitura3-ponto-${ponto}" 
                                step="0.001" placeholder="0.000" value="${leitura3Val}">
                        </td>
                        <td>
                            <input type="number" class="form-control form-control-sm" 
                                id="leitura4-ponto-${ponto}" 
                                step="0.001" placeholder="0.000" value="${leitura4Val}">
                        </td>
                        ${exibeIncerteza ? `
                        <td>
                            <input type="number" class="form-control form-control-sm" 
                                id="incerteza-ponto-${ponto}" 
                                step="0.0001" placeholder="0.0000" min="0"
                                title="Incerteza de medição (obrigatório para certificado ISO 17025)">
                        </td>
                        ` : ''}
                        ${podeRemover ? `
                            <td>
                                <button type="button" class="btn btn-sm btn-outline-danger" 
                                    onclick="removerPonto('${ponto}')" 
                                    title="Remover ponto ${ponto}">
                                    <i data-feather="trash-2" style="width: 14px; height: 14px;"></i>
                                </button>
                            </td>
                        ` : ''}
                    </tr>
                `;
                }).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = tabela;
    
    // Atualizar ícones Feather
    setTimeout(() => {
        if (typeof atualizarFeatherIcons === 'function') {
            atualizarFeatherIcons();
        } else if (typeof feather !== 'undefined' && feather.replace) {
            try {
                feather.replace();
            } catch (e) {
            }
        }
    }, 50);
    
    // Atualizar campos de carga com o valor atual (autocompletar)
    // Usar setTimeout para garantir que o DOM foi atualizado
    setTimeout(() => {
        if (pesosEnsaiosState.cargaAtual) {
            atualizarCargasMedicoes(pesosEnsaiosState.cargaAtual);
        }
    }, 200);
}

/**
 * Salvar ensaio final
 */
async function salvarEnsaioFinal() {
    await salvarEnsaio('final');
}

/**
 * Salvar ensaio (inicial ou final)
 */
async function salvarEnsaio(tipo) {
    if (!pesosEnsaiosState.processoId || !pesosEnsaiosState.balancaId) {
        mostrarAlerta('Processo ou balança não encontrado', 'danger');
        return;
    }
    
    const tipoEnsaioSelect = document.getElementById('tipoEnsaioSelect');
    const tipoEnsaio = tipoEnsaioSelect?.value;
    
    if (!tipoEnsaio) {
        mostrarAlerta('Selecione o tipo de ensaio', 'warning');
        return;
    }
    
    let medicoes = [];
    
    if (tipoEnsaio === 'mobilidade') {
        // Mobilidade: uma medição com Carga, Sobrecarga, Leitura antes/depois, Padrão utilizado (PESOPADRAO)
        const cargaEl = document.getElementById('carga-mobilidade');
        const sobrecargaEl = document.getElementById('sobrecarga-mobilidade');
        const leituraAntesEl = document.getElementById('leitura-antes-mobilidade');
        const leituraDepoisEl = document.getElementById('leitura-depois-mobilidade');
        const selectPadrao = document.getElementById('selectPadraoUtilizadoMobilidade');
        const padraoTextoEl = document.getElementById('padrao-utilizado-mobilidade-text');
        const carga = cargaEl?.value ? parseFloat(cargaEl.value) : null;
        const sobrecarga = sobrecargaEl?.value ? parseFloat(sobrecargaEl.value) : null;
        const leituraAntes = leituraAntesEl?.value ? parseFloat(leituraAntesEl.value) : null;
        const leituraDepois = leituraDepoisEl?.value ? parseFloat(leituraDepoisEl.value) : null;
        const padraoUtilizadoId = selectPadrao?.value ? parseInt(selectPadrao.value, 10) : null;
        const padraoUtilizado = (padraoTextoEl && padraoTextoEl.textContent) ? padraoTextoEl.textContent.trim() : null;
        if (carga == null || sobrecarga == null || leituraAntes == null || leituraDepois == null) {
            mostrarAlerta('Preencha Carga, Sobrecarga e Leituras (antes/depois) e selecione o padrão PESOPADRAO', 'warning');
            return;
        }
        medicoes = [{
            ponto: 1,
            carga: String(carga),
            sobrecarga: String(sobrecarga),
            leitura_antes: String(leituraAntes),
            leitura_depois: String(leituraDepois),
            padrao_utilizado: padraoUtilizado || null,
            padrao_utilizado_id: padraoUtilizadoId || null,
            ordem_execucao: 1,
            timestamp: Date.now()
        }];
    } else {
        // Excentricidade / Indicação: validar composição e coletar por pontos
        if (!pesosEnsaiosState.idsSelecionados.length || !pesosEnsaiosState.cargaAtual) {
            mostrarAlerta('Defina a carga e a composição primeiro', 'warning');
            return;
        }
        const pontos = pesosEnsaiosState.pontosDinamicos.length > 0 
            ? pesosEnsaiosState.pontosDinamicos 
            : (tipoEnsaio === 'excentricidade' ? ['A', 'B'] : 
               tipoEnsaio === 'indicacao' ? ['1', '2'] : 
               ['1']);
        
        const exibeIncerteza = (tipoEnsaio === 'indicacao' || tipoEnsaio === 'excentricidade');
        const fatorAbrangenciaEl = document.getElementById('fator-abrangencia-global');
        const fatorAbrangencia = fatorAbrangenciaEl?.value ? parseFloat(fatorAbrangenciaEl.value) : 2;
        
        for (let idx = 0; idx < pontos.length; idx++) {
            const pontoLabel = pontos[idx];
            const cargaEl = document.getElementById(`carga-ponto-${pontoLabel}`);
            const leitura1El = document.getElementById(`leitura1-ponto-${pontoLabel}`);
            const leitura2El = document.getElementById(`leitura2-ponto-${pontoLabel}`);
            const leitura3El = document.getElementById(`leitura3-ponto-${pontoLabel}`);
            const leitura4El = document.getElementById(`leitura4-ponto-${pontoLabel}`);
            const incertezaEl = exibeIncerteza ? document.getElementById(`incerteza-ponto-${pontoLabel}`) : null;
            
            const carga = parseFloat(cargaEl?.value || pesosEnsaiosState.cargaAtual);
            const leitura1 = leitura1El?.value ? parseFloat(leitura1El.value) : null;
            const leitura2 = leitura2El?.value ? parseFloat(leitura2El.value) : null;
            const leitura3 = leitura3El?.value ? parseFloat(leitura3El.value) : null;
            const leitura4 = leitura4El?.value ? parseFloat(leitura4El.value) : null;
            const incertezaVal = incertezaEl?.value != null && incertezaEl.value.trim() !== '' 
                ? parseFloat(incertezaEl.value) : null;
            
            if (!leitura1 && !leitura2 && !leitura3 && !leitura4) {
                mostrarAlerta(`Preencha pelo menos uma leitura para o ponto ${pontoLabel}`, 'warning');
                return;
            }
            
            // ISO 17025: incerteza obrigatória no ensaio final (indicação/excentricidade) para certificado
            if (tipo === 'final' && exibeIncerteza && (incertezaVal == null || incertezaVal < 0)) {
                mostrarAlerta(`Informe a incerteza de medição para o ponto ${pontoLabel} (obrigatório para certificado ISO 17025)`, 'warning');
                return;
            }
            
            let validadeMin = pesosEnsaiosState.conjunto?.validade_min;
            if (validadeMin && typeof validadeMin === 'string') {
                validadeMin = validadeMin.split('T')[0];
            }
            const pesosResumo = pesosEnsaiosState.resumoSelecionado.map(item => ({
                id: item.id,
                valor_nominal: String(item.valor_nominal || 0),
                unidade: item.unidade || 'kg',
                classe: item.classe || null,
                identificador: item.identificador || `ID ${item.id}`
            }));
            
            const medicaoItem = {
                ponto: idx + 1,
                carga: String(carga),
                pesos_ids: pesosEnsaiosState.idsSelecionados,
                pesos_resumo: pesosResumo.length > 0 ? pesosResumo : null,
                certificado_numero: pesosEnsaiosState.conjunto?.certificado_numero || null,
                validade_min: validadeMin || null,
                leitura_1: leitura1 !== null ? String(leitura1) : null,
                leitura_2: leitura2 !== null ? String(leitura2) : null,
                leitura_3: leitura3 !== null ? String(leitura3) : null,
                leitura_4: leitura4 !== null ? String(leitura4) : null,
                ordem_execucao: idx + 1,
                timestamp: Date.now()
            };
            if (exibeIncerteza) {
                medicaoItem.incerteza = incertezaVal != null ? String(incertezaVal) : null;
                medicaoItem.fator_abrangencia = fatorAbrangencia;
            }
            medicoes.push(medicaoItem);
        }
    }
    
    // Montar payload (medicoes + tipo_ensaio para gravar excentricidade/mobilidade na balança)
    const payload = {
        medicoes: medicoes,
        tipo_ensaio: tipoEnsaio || null
    };
    
    // Determinar endpoint
    const endpoint = tipo === 'inicial' 
        ? `/api/v1/processos/${pesosEnsaiosState.processoId}/balancas/${pesosEnsaiosState.balancaId}/ensaios/medicoes`
        : `/api/v1/processos/${pesosEnsaiosState.processoId}/balancas/${pesosEnsaiosState.balancaId}/ensaios/medicoes-final`;
    
    try {
        // Usar getCookie do escopo global ou função auxiliar
        const getCookieFunc = typeof getCookie !== 'undefined' ? getCookie : function(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        };
        
        const token = getCookieFunc('pdv_automscale_token');
        if (!token) {
            throw new Error('Token de autenticação não encontrado. Faça login novamente.');
        }
        
        const fetchFn = window.authenticatedFetch || fetch;
        const response = await fetchFn(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            let errorDetail = 'Erro ao salvar ensaio';
            try {
                const error = await response.json();
                if (typeof error.detail === 'string') {
                    errorDetail = error.detail;
                } else if (Array.isArray(error.detail) && error.detail.length > 0 && error.detail[0].msg) {
                    errorDetail = error.detail.map(d => d.msg).join(' ');
                } else {
                    errorDetail = error.message || JSON.stringify(error);
                }
            } catch (e) {
                const errorText = await response.text();
                errorDetail = errorText || `Erro HTTP ${response.status}`;
            }
            // 422 equipamento auxiliar vencido: modal inline por 2s (padrão MAPA_SISTEMA)
            if (response.status === 422 && errorDetail.includes('equipamento auxiliar vencido')) {
                if (typeof abrirModalEquipAuxVencido === 'function') {
                    abrirModalEquipAuxVencido(errorDetail);
                    setTimeout(() => { if (typeof fecharModalEquipAuxVencido === 'function') fecharModalEquipAuxVencido(); }, 2000);
                } else {
                    mostrarAlerta(errorDetail, 'danger');
                }
                return;
            }
            // 422 pesos vencidos: exibir modal inline por 2s (padrão MAPA_SISTEMA), mantendo bloqueio
            if (response.status === 422 && (errorDetail.includes('vencidos') || errorDetail.includes('pesos padrão vencidos') || errorDetail.includes('Peças vencidas'))) {
                if (typeof abrirModalPesosVencidos === 'function') {
                    abrirModalPesosVencidos(errorDetail);
                    setTimeout(() => { if (typeof fecharModalPesosVencidos === 'function') fecharModalPesosVencidos(); }, 2000);
                } else {
                    mostrarAlerta(errorDetail, 'danger');
                }
                return;
            }
            throw new Error(errorDetail);
        }
        
        const data = await response.json();
        mostrarAlerta(`✅ Ensaio ${tipo} salvo com sucesso!`, 'success');
        
        // Limpar campos de leitura após salvar (apenas excentricidade/indicação; mobilidade não)
        if (tipoEnsaioSelect.value !== 'mobilidade') {
            const pontos = pesosEnsaiosState.pontosDinamicos.length > 0 
                ? pesosEnsaiosState.pontosDinamicos 
                : (tipoEnsaioSelect.value === 'excentricidade' ? ['A', 'B'] : 
                   tipoEnsaioSelect.value === 'indicacao' ? ['1', '2'] : 
                   ['1']);
            pontos.forEach((pontoLabel) => {
                const leitura1El = document.getElementById(`leitura1-ponto-${pontoLabel}`);
                const leitura2El = document.getElementById(`leitura2-ponto-${pontoLabel}`);
                const leitura3El = document.getElementById(`leitura3-ponto-${pontoLabel}`);
                const leitura4El = document.getElementById(`leitura4-ponto-${pontoLabel}`);
                if (leitura1El) leitura1El.value = '';
                if (leitura2El) leitura2El.value = '';
                if (leitura3El) leitura3El.value = '';
                if (leitura4El) leitura4El.value = '';
            });
        }
        
    } catch (error) {
        
        // Melhorar mensagem de erro para pesos/equip aux vencidos
        let mensagemErro = error.message;
        if (mensagemErro.includes('equipamento auxiliar vencido')) {
            mensagemErro = `⚠️ Não é permitido usar equipamento auxiliar vencido no processo.\n\n` +
                          `Por favor, renove o certificado dos equipamentos ou vincule equipamentos válidos.`;
        } else if (mensagemErro.includes('Peças vencidas') || mensagemErro.includes('pesos padrão vencidos')) {
            mensagemErro = `⚠️ Não é possível usar pesos padrão vencidos no ensaio.\n\n` +
                          `Por favor:\n` +
                          `1. Verifique a data de validade dos pesos utilizados\n` +
                          `2. Renove o certificado dos pesos vencidos, ou\n` +
                          `3. Use pesos válidos para realizar o ensaio\n\n` +
                          `Detalhes: ${mensagemErro}`;
        }
        
        mostrarAlerta(`Erro ao salvar ensaio ${tipo}: ` + mensagemErro, 'danger');
    }
}

/**
 * Abrir modal de pesos vencidos (422) - Padrão MAPA_SISTEMA: CSS inline
 * Fecha automaticamente em 2s (agendado pelo chamador).
 */
function abrirModalPesosVencidos(mensagem) {
    const modal = document.getElementById('modalPesosVencidosCustom');
    const bodyEl = document.getElementById('modalPesosVencidosMensagem');
    if (modal) {
        if (bodyEl) bodyEl.textContent = mensagem || 'Não é permitido usar pesos padrão vencidos no ensaio.';
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
}

/**
 * Fechar modal de pesos vencidos
 */
function fecharModalPesosVencidos() {
    const modal = document.getElementById('modalPesosVencidosCustom');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

/**
 * Abrir modal equipamento auxiliar vencido (422) - Padrão MAPA_SISTEMA: CSS inline
 */
function abrirModalEquipAuxVencido(mensagem) {
    const modal = document.getElementById('modalEquipAuxVencidoCustom');
    const bodyEl = document.getElementById('modalEquipAuxVencidoMensagem');
    if (modal) {
        if (bodyEl) bodyEl.textContent = mensagem || 'Não é permitido usar equipamento auxiliar vencido no processo.';
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
}

/**
 * Fechar modal equipamento auxiliar vencido
 */
function fecharModalEquipAuxVencido() {
    const modal = document.getElementById('modalEquipAuxVencidoCustom');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

/**
 * Mostrar alerta Bootstrap
 */
function mostrarAlerta(mensagem, tipo = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${tipo} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.modal-equipamento-body') || document.body;
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Exportar funções globais para uso no template
window.inicializarPesosEnsaios = inicializarPesosEnsaios;
window.definirCarga = definirCarga;
window.atualizarSomaModal = atualizarSomaModal;
window.comporAutomaticamente = comporAutomaticamente;
window.abrirModalAjusteManual = abrirModalAjusteManual;
window.fecharModalAjusteManualPesos = fecharModalAjusteManualPesos;
window.aplicarAjusteManual = aplicarAjusteManual;
window.salvarEnsaioFinal = salvarEnsaioFinal;
window.adicionarPonto = adicionarPonto;
window.removerPonto = removerPonto;
window.abrirModalPesosVencidos = abrirModalPesosVencidos;
window.fecharModalPesosVencidos = fecharModalPesosVencidos;