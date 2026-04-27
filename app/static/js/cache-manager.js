/**
 * PDV Ibix - Gerenciador de Cache
 * Limpa caches antigos e otimiza performance
 */

(function() {
    'use strict';
    
    console.log('🧹 Cache Manager - Inicializando...');
    
    // Versão atual do cache (incrementar quando houver mudanças grandes)
    const CACHE_VERSION = '2.0';
    
    /**
     * Verificar e limpar caches antigos
     */
    function checkAndCleanOldCache() {
        const currentVersion = localStorage.getItem('pdv_automscale_cache_version');
        
        if (currentVersion !== CACHE_VERSION) {
            console.log(`🧹 Limpando caches antigos (versão ${currentVersion} → ${CACHE_VERSION})`);
            
            // Limpar apenas caches de dados, manter token
            const keysToRemove = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith('pdv_automscale_') && key !== 'pdv_automscale_token') {
                    keysToRemove.push(key);
                }
            }
            
            keysToRemove.forEach(key => {
                localStorage.removeItem(key);
                console.log(`  ✓ Removido: ${key}`);
            });
            
            // Atualizar versão
            localStorage.setItem('pdv_automscale_cache_version', CACHE_VERSION);
            console.log('✅ Cache atualizado para versão', CACHE_VERSION);
        } else {
            console.log(`✅ Cache na versão atual (${CACHE_VERSION})`);
        }
    }
    
    /**
     * Limpar caches expirados
     */
    function cleanExpiredCaches() {
        const now = Date.now();
        const maxAge = 3600000; // 1 hora
        
        // Verificar timestamp do cache de usuário
        const userDataTime = localStorage.getItem('pdv_automscale_user_data_timestamp');
        if (userDataTime) {
            const age = now - parseInt(userDataTime);
            if (age > maxAge) {
                console.log('🧹 Cache de usuário expirado, removendo...');
                localStorage.removeItem('pdv_automscale_user_data');
                localStorage.removeItem('pdv_automscale_user_data_timestamp');
            }
        }
    }
    
    /**
     * Otimizar localStorage
     */
    function optimizeStorage() {
        try {
            // Verificar tamanho do localStorage
            let totalSize = 0;
            for (let key in localStorage) {
                if (localStorage.hasOwnProperty(key)) {
                    totalSize += localStorage[key].length;
                }
            }
            
            // Se passar de 1MB, limpar caches não essenciais
            if (totalSize > 1048576) {
                console.log('⚠️  localStorage grande, limpando caches não essenciais...');
                
                // Manter apenas dados essenciais
                const essentialKeys = ['pdv_automscale_token', 'pdv_automscale_user_data', 'pdv_automscale_cache_version'];
                for (let key in localStorage) {
                    if (localStorage.hasOwnProperty(key) && !essentialKeys.includes(key)) {
                        if (key.startsWith('pdv_automscale_')) {
                            localStorage.removeItem(key);
                            console.log(`  ✓ Removido cache: ${key}`);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('❌ Erro ao otimizar storage:', error);
        }
    }
    
    /**
     * Função pública para forçar limpeza total
     */
    window.clearCertipesoCache = function() {
        console.log('🧹 Limpando TODOS os caches do PDV Ibix...');
        
        const token = localStorage.getItem('pdv_automscale_token');
        
        // Remover tudo
        const keys = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('pdv_automscale_')) {
                keys.push(key);
            }
        }
        
        keys.forEach(key => localStorage.removeItem(key));
        
        // Restaurar token se havia
        if (token) {
            localStorage.setItem('pdv_automscale_token', token);
        }
        
        // Definir versão
        localStorage.setItem('pdv_automscale_cache_version', CACHE_VERSION);
        
        console.log('✅ Caches limpos! Recarregue a página.');
        
        return true;
    };
    
    // Executar limpezas automáticas
    checkAndCleanOldCache();
    cleanExpiredCaches();
    optimizeStorage();
    
    console.log('✅ Cache Manager - Inicializado');
    
})();

