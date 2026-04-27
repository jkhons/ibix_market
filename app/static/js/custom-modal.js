/**
 * PDV Ibix - Sistema de Modal Customizado
 * Script para gerenciar modais independentes sem Bootstrap
 */

class CustomModal {
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
        if (!this.modal) return;
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
        if (!this.modal) return;
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
let modalNovoUsuario;
let modalConfirmacao;
let modalNovaRole;
let modalConfirmarExclusaoRole;
let modalGerenciarPermissoes;
let modalAdicionarPermissoes;

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('modalNovoUsuario')) modalNovoUsuario = new CustomModal('modalNovoUsuario');
    if (document.getElementById('modalConfirmacao')) modalConfirmacao = new CustomModal('modalConfirmacao');
    if (document.getElementById('modalNovaRole')) modalNovaRole = new CustomModal('modalNovaRole');
    if (document.getElementById('modalConfirmarExclusaoRole')) modalConfirmarExclusaoRole = new CustomModal('modalConfirmarExclusaoRole');
    if (document.getElementById('modalGerenciarPermissoes')) modalGerenciarPermissoes = new CustomModal('modalGerenciarPermissoes');
    if (document.getElementById('modalAdicionarPermissoes')) modalAdicionarPermissoes = new CustomModal('modalAdicionarPermissoes');
    
    // Botão Novo Usuário
    const btnNovoUsuario = document.getElementById('btnNovoUsuario');
    if (btnNovoUsuario) {
        btnNovoUsuario.addEventListener('click', () => {
            modalNovoUsuario.open();
        });
    }
    // Botão Novo Administrador (apenas Super Admin): abre o mesmo modal com função Administrador pré-selecionada
    const btnNovoAdministrador = document.getElementById('btnNovoAdministrador');
    if (btnNovoAdministrador && modalNovoUsuario) {
        btnNovoAdministrador.addEventListener('click', () => {
            modalNovoUsuario.open();
            document.dispatchEvent(new CustomEvent('modalNovoAdministradorOpened'));
        });
    }
    
    // Botões de cancelar
    const btnCancelarModal = document.getElementById('btnCancelarModal');
    if (btnCancelarModal) {
        btnCancelarModal.addEventListener('click', () => {
            modalNovoUsuario.close();
        });
    }
    
    const btnCancelarExclusao = document.getElementById('btnCancelarExclusao');
    if (btnCancelarExclusao) {
        btnCancelarExclusao.addEventListener('click', () => {
            modalConfirmacao.close();
        });
    }
    
    const btnCloseModalConfirmacao = document.getElementById('btnCloseModalConfirmacao');
    if (btnCloseModalConfirmacao) {
        btnCloseModalConfirmacao.addEventListener('click', () => {
            modalConfirmacao.close();
        });
    }
    
    // Botões do modal de Role
    const btnCloseModalRole = document.getElementById('btnCloseModalRole');
    if (btnCloseModalRole) {
        btnCloseModalRole.addEventListener('click', () => {
            modalNovaRole.close();
        });
    }
    
    const btnCloseModalConfirmarRole = document.getElementById('btnCloseModalConfirmarRole');
    if (btnCloseModalConfirmarRole) {
        btnCloseModalConfirmarRole.addEventListener('click', () => {
            modalConfirmarExclusaoRole.close();
        });
    }
    
    // Botões do modal de permissões
    const btnCancelarPermissoes = document.getElementById('btnCancelarPermissoes');
    if (btnCancelarPermissoes) {
        btnCancelarPermissoes.addEventListener('click', () => {
            modalGerenciarPermissoes.close();
        });
    }
    
    // Eventos do modal Adicionar Permissões
    const btnCloseModalAdicionarPermissoes = document.getElementById('btnCloseModalAdicionarPermissoes');
    if (btnCloseModalAdicionarPermissoes && modalAdicionarPermissoes) {
        btnCloseModalAdicionarPermissoes.addEventListener('click', () => {
            modalAdicionarPermissoes.close();
        });
    }
    
    const btnCancelarAdicionarPermissoes = document.getElementById('btnCancelarAdicionarPermissoes');
    if (btnCancelarAdicionarPermissoes && modalAdicionarPermissoes) {
        btnCancelarAdicionarPermissoes.addEventListener('click', () => {
            modalAdicionarPermissoes.close();
        });
    }
});

