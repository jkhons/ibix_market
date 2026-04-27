/**
 * PDV Ibix - Sistema de Modal Customizado para Roles
 * Script para gerenciar modais independentes sem Bootstrap
 */

class CustomModalRoles {
    constructor(modalId) {
        this.modal = document.getElementById(modalId);
        this.overlay = document.getElementById('modalOverlay');
        this.isOpen = false;
        
        if (!this.modal) {
            console.error(`Modal ${modalId} não encontrado`);
            return;
        }
        
        this.init();
    }
    
    init() {
        // Fechar ao clicar no X
        const closeBtn = this.modal.querySelector('.custom-modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }
        
        // Fechar ao clicar no overlay
        if (this.overlay) {
            this.overlay.addEventListener('click', () => this.close());
        }
        
        // Fechar com ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
    }
    
    open() {
        this.modal.classList.add('active');
        if (this.overlay) {
            this.overlay.classList.add('active');
        }
        this.isOpen = true;
        document.body.style.overflow = 'hidden';
        
        // Atualizar ícones Feather
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
    
    close() {
        this.modal.classList.remove('active');
        if (this.overlay) {
            this.overlay.classList.remove('active');
        }
        this.isOpen = false;
        document.body.style.overflow = '';
        
        // Trigger custom event ao fechar
        const event = new CustomEvent('modalClosed', { detail: { modalId: this.modal.id } });
        document.dispatchEvent(event);
    }
    
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }
}

// Instâncias globais dos modais
let modalNovaRole;
let modalConfirmacaoRole;

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    modalNovaRole = new CustomModalRoles('modalNovaRole');
    modalConfirmacaoRole = new CustomModalRoles('modalConfirmacao');
    
    // Botão Nova Role
    const btnNovaRole = document.getElementById('btnNovaRole');
    if (btnNovaRole) {
        btnNovaRole.addEventListener('click', () => {
            modalNovaRole.open();
        });
    }
    
    // Botões de cancelar
    const btnCancelarModal = document.getElementById('btnCancelarModal');
    if (btnCancelarModal) {
        btnCancelarModal.addEventListener('click', () => {
            modalNovaRole.close();
        });
    }
    
    const btnCancelarExclusao = document.getElementById('btnCancelarExclusao');
    if (btnCancelarExclusao) {
        btnCancelarExclusao.addEventListener('click', () => {
            modalConfirmacaoRole.close();
        });
    }
    
    const btnCloseModalConfirmacao = document.getElementById('btnCloseModalConfirmacao');
    if (btnCloseModalConfirmacao) {
        btnCloseModalConfirmacao.addEventListener('click', () => {
            modalConfirmacaoRole.close();
        });
    }
});

