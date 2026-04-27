/**
 * PDV Ibix - Sistema de Alertas
 * Gerencia alertas e notificações em todo o sistema
 */

class AlertSystem {
    constructor() {
        this.alertQueue = [];
        this.isProcessing = false;
        this.init();
    }
    
    init() {
        // Criar container de alertas se não existir
        this.createAlertContainer();
        
        // Processar fila de alertas
        this.processQueue();
    }
    
    createAlertContainer() {
        // Verificar se já existe um container de alertas
        let alertContainer = document.getElementById('alert-container');
        
        if (!alertContainer) {
            // Buscar container principal
            let mainContainer = document.querySelector('.container-fluid');
            if (!mainContainer) {
                mainContainer = document.querySelector('.container');
            }
            if (!mainContainer) {
                mainContainer = document.body;
            }
            
            // Criar container de alertas
            alertContainer = document.createElement('div');
            alertContainer.id = 'alert-container';
            alertContainer.className = 'mb-3';
            alertContainer.style.cssText = 'position: relative; z-index: 1000;';
            
            // Inserir no início do container principal
            if (mainContainer === document.body) {
                // Se não houver container específico, usar position fixed
                alertContainer.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px; max-width: 400px;';
                document.body.appendChild(alertContainer);
            } else {
                mainContainer.insertBefore(alertContainer, mainContainer.firstChild);
            }
        }
        
        this.alertContainer = alertContainer;
    }
    
    show(message, type = 'info', duration = 5000) {
        // Adicionar à fila
        this.alertQueue.push({
            message: message,
            type: type,
            duration: duration,
            timestamp: Date.now()
        });
        
        // Processar fila se não estiver processando
        if (!this.isProcessing) {
            this.processQueue();
        }
    }
    
    processQueue() {
        if (this.alertQueue.length === 0) {
            this.isProcessing = false;
            return;
        }
        
        this.isProcessing = true;
        
        // Processar próximo alerta
        const alert = this.alertQueue.shift();
        this.createAlert(alert);
        
        // Processar próximo após um pequeno delay
        setTimeout(() => {
            this.processQueue();
        }, 100);
    }
    
    createAlert(alertData) {
        const { message, type, duration } = alertData;
        
        // Criar elemento de alerta
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.style.cssText = 'margin-bottom: 10px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Adicionar ao container
        this.alertContainer.appendChild(alertDiv);
        
        // Animar entrada
        setTimeout(() => {
            alertDiv.classList.add('show');
        }, 10);
        
        // Remover após duração especificada
        setTimeout(() => {
            this.removeAlert(alertDiv);
        }, duration);
        
        // Adicionar evento de fechar
        const closeBtn = alertDiv.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.removeAlert(alertDiv);
            });
        }
    }
    
    removeAlert(alertDiv) {
        if (alertDiv && alertDiv.parentNode) {
            alertDiv.classList.remove('show');
            alertDiv.classList.add('fade');
            
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 150);
        }
    }
    
    // Métodos de conveniência
    success(message, duration = 5000) {
        this.show(message, 'success', duration);
    }
    
    error(message, duration = 7000) {
        this.show(message, 'danger', duration);
    }
    
    warning(message, duration = 6000) {
        this.show(message, 'warning', duration);
    }
    
    info(message, duration = 5000) {
        this.show(message, 'info', duration);
    }
    
    // Limpar todos os alertas
    clearAll() {
        if (this.alertContainer) {
            this.alertContainer.innerHTML = '';
        }
        this.alertQueue = [];
        this.isProcessing = false;
    }
}

// Criar instância global
window.alertSystem = new AlertSystem();

// Função global para compatibilidade
window.mostrarAlerta = function(message, type, duration) {
    window.alertSystem.show(message, type, duration);
};

// Funções de conveniência globais
window.mostrarSucesso = function(message, duration) {
    window.alertSystem.success(message, duration);
};

window.mostrarErro = function(message, duration) {
    window.alertSystem.error(message, duration);
};

window.mostrarAviso = function(message, duration) {
    window.alertSystem.warning(message, duration);
};

window.mostrarInfo = function(message, duration) {
    window.alertSystem.info(message, duration);
};

document.addEventListener('DOMContentLoaded', function() {}); 