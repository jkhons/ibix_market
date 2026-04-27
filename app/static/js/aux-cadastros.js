/**
 * PDV Ibix - Funções Auxiliares para Cadastros Auxiliares Unificados
 * 
 * Este arquivo contém funções para trabalhar com a estrutura unificada
 * de certificados auxiliares (aux_cadastros).
 * 
 * Substitui as chamadas antigas para:
 * - /api/v1/certificados-auxiliares
 * - /api/v1/inspetores-aprovadores
 * 
 * Por:
 * - /api/v1/aux-cadastros
 * - /api/v1/processos/{id}/balancas/{id}/aux-cadastros
 */

/**
 * Obtém o token de autenticação do cookie
 * @returns {string|null}
 */
function getToken() {
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }
    return getCookie('pdv_automscale_token');
}

/**
 * Carrega cadastros auxiliares por categoria
 * @param {string} categoriaCodigo - TERMOBAROHIGROMETRO, PESO, INSPETOR_APROVADOR
 * @param {object} filtros - {ativo: bool, skip: int, limit: int, tipo: string (apenas para INSPETOR_APROVADOR)}
 * @returns {Promise<Array>}
 */
async function carregarAuxCadastros(categoriaCodigo, filtros = {}) {
    try {
        const params = new URLSearchParams({
            categoria_codigo: categoriaCodigo,
            ativo: filtros.ativo !== undefined ? filtros.ativo : true,
            skip: filtros.skip || 0,
            limit: filtros.limit || 100
        });
        
        // Para INSPETOR_APROVADOR, pode filtrar por tipo (inspetor/aprovador) via atributos_json
        // Mas isso será feito no backend, então não passamos aqui
        
        const fetchFn = window.authenticatedFetch || fetch;
        const response = await fetchFn(`/api/v1/aux-cadastros?${params}`, {
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `Erro ao carregar cadastros: ${response.statusText}`);
        }
        
        const data = await response.json();
        // Compatibilidade: pode retornar {cadastros: [...]} ou array direto
        let cadastros = Array.isArray(data) ? data : (data.cadastros || []);
        
        // Se for INSPETOR_APROVADOR e tiver filtro de tipo, filtrar localmente
        if (categoriaCodigo === 'INSPETOR_APROVADOR' && filtros.tipo) {
            cadastros = cadastros.filter(cad => {
                const atributos = cad.atributos_json || {};
                return atributos.tipo === filtros.tipo;
            });
        }
        
        return cadastros;
    } catch (error) {
        console.error(`❌ Erro ao carregar cadastros (${categoriaCodigo}):`, error);
        throw error;
    }
}

/**
 * Adiciona vínculo auxiliar a uma balança
 * @param {number} processoId
 * @param {number} balancaId
 * @param {number} auxCadastroId
 * @param {string} papel - equipamento_auxiliar, peso_padrao, inspetor, aprovador
 * @param {number} ordem - Opcional, apenas para peso_padrao
 * @returns {Promise<Object>}
 */
async function adicionarVinculoAuxiliar(processoId, balancaId, auxCadastroId, papel, ordem = null) {
    try {
        const body = {
            aux_cadastro_id: auxCadastroId,
            papel: papel
        };
        
        if (papel === 'peso_padrao' && ordem !== null) {
            body.ordem = ordem;
        }
        
        const url = `/api/v1/processos/${processoId}/balancas/${balancaId}/aux-cadastros`;
        console.log('📤 Adicionando vínculo auxiliar:', { url, body });
        
        const fetchFn = window.authenticatedFetch || fetch;
        const response = await fetchFn(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify(body)
        });
        
        console.log('📥 Resposta da API - Status:', response.status, response.statusText);
        console.log('📥 Headers:', Object.fromEntries(response.headers.entries()));
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Erro na resposta:', errorText);
            let error;
            try {
                error = JSON.parse(errorText);
            } catch {
                error = { detail: errorText || response.statusText };
            }
            throw new Error(error.detail || `Erro ${response.status}: ${response.statusText}`);
        }
        
        // Verificar se há conteúdo na resposta
        const contentType = response.headers.get('content-type');
        const contentLength = response.headers.get('content-length');
        
        console.log('📥 Content-Type:', contentType, 'Content-Length:', contentLength);
        
        // Se não há conteúdo, pode ser 204 No Content
        if (response.status === 204 || contentLength === '0') {
            console.warn('⚠️ Resposta sem conteúdo (204 No Content)');
            throw new Error('Resposta vazia da API (204 No Content). O endpoint pode não estar retornando dados.');
        }
        
        // Tentar fazer parse do JSON
        let data;
        try {
            const text = await response.text();
            console.log('📥 Resposta texto bruto:', text);
            
            if (!text || text.trim() === '') {
                throw new Error('Resposta vazia da API');
            }
            
            data = JSON.parse(text);
            console.log('✅ Dados retornados pela API (adicionarVinculoAuxiliar):', data);
        } catch (parseError) {
            console.error('❌ Erro ao fazer parse do JSON:', parseError);
            throw new Error(`Erro ao processar resposta da API: ${parseError.message}`);
        }
        
        if (!data) {
            throw new Error('Resposta vazia da API');
        }
        
        return data;
    } catch (error) {
        console.error('❌ Erro ao adicionar vínculo auxiliar:', error);
        throw error;
    }
}

/**
 * Lista vínculos auxiliares de uma balança
 * @param {number} processoId
 * @param {number} balancaId
 * @param {string} papel - Opcional, filtrar por papel
 * @returns {Promise<Array>}
 */
async function listarVinculosAuxiliares(processoId, balancaId, papel = null) {
    try {
        const params = new URLSearchParams();
        if (papel) {
            params.append('papel', papel);
        }
        
        const url = `/api/v1/processos/${processoId}/balancas/${balancaId}/aux-cadastros${params.toString() ? '?' + params : ''}`;
        
        const fetchFn = window.authenticatedFetch || fetch;
        const response = await fetchFn(url, {
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `Erro ao listar vínculos: ${response.statusText}`);
        }
        
        const data = await response.json();
        // Pode retornar array direto ou objeto com lista
        return Array.isArray(data) ? data : (data.vinculos || data.items || []);
    } catch (error) {
        console.error('❌ Erro ao listar vínculos auxiliares:', error);
        throw error;
    }
}

/**
 * Remove vínculo auxiliar de uma balança
 * @param {number} processoId
 * @param {number} balancaId
 * @param {number} vinculoId
 * @returns {Promise<void>}
 */
async function removerVinculoAuxiliar(processoId, balancaId, vinculoId) {
    try {
        const fetchFn = window.authenticatedFetch || fetch;
        const response = await fetchFn(
            `/api/v1/processos/${processoId}/balancas/${balancaId}/aux-cadastros/${vinculoId}`,
            {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${getToken()}`
                }
            }
        );
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || 'Erro ao remover vínculo');
        }
        
        return await response.json().catch(() => ({}));
    } catch (error) {
        console.error('❌ Erro ao remover vínculo auxiliar:', error);
        throw error;
    }
}

// ============================================================================
// FUNÇÕES ESPECÍFICAS (CONVENIÊNCIA)
// ============================================================================

/**
 * Carrega equipamentos auxiliares (TERMOBAROHIGROMETRO)
 * @param {object} filtros - {ativo: bool, skip: int, limit: int}
 * @returns {Promise<Array>}
 */
async function carregarEquipamentosAuxiliares(filtros = {}) {
    return await carregarAuxCadastros('TERMOBAROHIGROMETRO', filtros);
}

/**
 * Adiciona equipamento auxiliar a uma balança
 * @param {number} processoId
 * @param {number} balancaId
 * @param {number} auxCadastroId
 * @returns {Promise<Object>}
 */
async function adicionarEquipamentoAuxiliar(processoId, balancaId, auxCadastroId) {
    return await adicionarVinculoAuxiliar(processoId, balancaId, auxCadastroId, 'equipamento_auxiliar');
}

/**
 * Carrega pesos padrão (PESO)
 * @param {object} filtros - {ativo: bool, skip: int, limit: int}
 * @returns {Promise<Array>}
 */
async function carregarPesosPadrao(filtros = {}) {
    return await carregarAuxCadastros('PESO', filtros);
}

/**
 * Adiciona peso padrão a uma balança
 * @param {number} processoId
 * @param {number} balancaId
 * @param {number} auxCadastroId
 * @param {number} ordem
 * @returns {Promise<Object>}
 */
async function adicionarPesoPadrao(processoId, balancaId, auxCadastroId, ordem) {
    return await adicionarVinculoAuxiliar(processoId, balancaId, auxCadastroId, 'peso_padrao', ordem);
}

/**
 * Carrega inspetores (INSPETOR_APROVADOR com tipo=inspetor)
 * @param {object} filtros - {ativo: bool, skip: int, limit: int}
 * @returns {Promise<Array>}
 */
async function carregarInspetores(filtros = {}) {
    return await carregarAuxCadastros('INSPETOR_APROVADOR', {...filtros, tipo: 'inspetor'});
}

/**
 * Adiciona inspetor a uma balança
 * @param {number} processoId
 * @param {number} balancaId
 * @param {number} auxCadastroId
 * @returns {Promise<Object>}
 */
async function adicionarInspetor(processoId, balancaId, auxCadastroId) {
    return await adicionarVinculoAuxiliar(processoId, balancaId, auxCadastroId, 'inspetor');
}

/**
 * Carrega aprovadores (INSPETOR_APROVADOR com tipo=aprovador)
 * @param {object} filtros - {ativo: bool, skip: int, limit: int}
 * @returns {Promise<Array>}
 */
async function carregarAprovadores(filtros = {}) {
    return await carregarAuxCadastros('INSPETOR_APROVADOR', {...filtros, tipo: 'aprovador'});
}

/**
 * Adiciona aprovador a uma balança
 * @param {number} processoId
 * @param {number} balancaId
 * @param {number} auxCadastroId
 * @returns {Promise<Object>}
 */
async function adicionarAprovador(processoId, balancaId, auxCadastroId) {
    return await adicionarVinculoAuxiliar(processoId, balancaId, auxCadastroId, 'aprovador');
}
