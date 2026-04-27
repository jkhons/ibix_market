# PDV Ibix - Models Module
from .abertura_caixa import AberturaCaixa

# Modelos Qualidade ISO 17025
from .acao_corretiva import AcaoCorretiva

# Access log (classificação visitantes HUMANO/BOT/CLOUD)
from .access_log import AccessLog

# Escopo por role (Saas.md Fase 3)
from .administrador_cliente import AdministradorCliente

# Vínculo Cliente Administrador → Administrador (hierarquia RBAC)
from .administrador_cliente_administrador import AdministradorClienteAdministrador

# Modelos de Alertas
from .alerta_email import AlertaEmail
from .alerta_enviado import AlertaEnviado
from .anuncio_plataforma import AnuncioPlataforma
from .app_versao_config import AppVersaoConfig

# Modelos do Cliente
from .area_cliente import AreaCliente

# Modelos de Controle
from .assinatura import Assinatura

# Audit log append-only (E4.4 confirmação de impl.)
from .audit_log import AuditLog
from .avaliacao_marketplace import AvaliacaoMarketplace

# Billing events (webhook idempotente E4.1/E5.4)
from .billing_event import BillingEvent
from .billing_notificacao import BillingNotificacao
from .billing_usage_event import BillingUsageEvent
from .caixa import Caixa
from .categoria_plataforma import CategoriaPlataforma
from .cliente import Cliente
from .cliente_administrador_cliente import ClienteAdministradorCliente

# Minha equipe (Saas.md Fase 6.2)
from .cliente_administrador_tecnico import ClienteAdministradorTecnico
from .codigo_barras_cliente import CodigoBarrasCliente
from .codigo_desconto import CodigoDesconto
from .configuracao import Configuracao
from .consumidor_consentimento import ConsumidorConsentimento
from .consumidor_favorito import ConsumidorFavorito
from .consumidor_marketplace import ConsumidorMarketplace
from .consumidor_notificacao import ConsumidorNotificacao

# Mobile App — Sprint 1
from .consumidor_push_token import ConsumidorPushToken
from .consumidor_refresh_token import ConsumidorRefreshToken
from .consumidor_social_identity import ConsumidorSocialIdentity
from .consumidor_social_link_pending import ConsumidorSocialLinkPending
from .contrato_aditivo import ContratoAditivo
from .contrato_comercial import ContratoComercial

# Mobile App — Sprint 3
from .conversa_marketplace import ConversaMarketplace
from .cupom_consumidor import CupomConsumidor
from .cupom_fiscal import CupomFiscal, CupomFiscalItem

# Mobile App — Sprint 2
from .cupom_marketplace import CupomMarketplace
from .devolucao_marketplace import DevolucaoMarketplace
from .divulgador import Divulgador
from .divulgador_regra import DivulgadorRegra
from .download_cliente import DownloadCliente

# Modelos Fiscais
from .empresa import Empresa
from .endereco_consumidor import EnderecoConsumidor
from .entrega_evento import EntregaEvento
from .entrega_marketplace import EntregaMarketplace

# Logística / entregador
from .entregador import Entregador
from .entregador_veiculo import EntregadorVeiculo

# Fase 3: estabelecimentos fiscais, venda pagamentos, movimentos caixa
from .estabelecimento_fiscal import EstabelecimentoFiscal
from .extrato_loja import ExtratoLoja
from .fiscal_documento import (
    FiscalAmbiente,
    FiscalDocumento,
    FiscalDocumentoDestinatarioSnapshot,
    FiscalDocumentoDuplicata,
    FiscalDocumentoEmitenteSnapshot,
    FiscalDocumentoItem,
    FiscalDocumentoItemImpostos,
    FiscalDocumentoTotais,
    FiscalDocumentoTransporte,
    FiscalEventoDocumento,
    FiscalFinalidadeEmissao,
    FiscalStatusDocumento,
    FiscalTipoDocumento,
    FiscalTipoEvento,
    FiscalTipoOperacao,
    FiscalTipoXml,
    FiscalXmlStore,
)
from .fiscal_download_log import FiscalDownloadLog
from .fiscal_evento import FiscalEvento
from .fornecedor_cliente import FornecedorCliente
from .google_cse_uso_log import GoogleCseUsoLog

# Modulo Influencers/Marketing
from .influencer_campanha import InfluencerCampanha
from .influencer_link import InfluencerLink
from .influencer_metrica import InfluencerMetrica
from .integration_event import IntegrationEvent

# Áreas de entrega (abrangência por cidade)
from .loja_area_entrega import LojaAreaEntrega

# Marketplace (loja na raiz para CA)
from .loja_marketplace import LojaMarketplace
from .loja_slug_history import LojaSlugHistory
from .marketing_vitrine_card import MarketingVitrineCard
from .marketing_vitrine_config import MarketingVitrineConfig
from .marketplace_checkout_session import MarketplaceCheckoutSession, MarketplaceCheckoutSessionPedido

# Modelos de Negócios
from .material_categoria import MaterialCategoria
from .mdfe import MDFe, MDFeCondutor, MDFeDocumento, MDFePercurso, MDFeVeiculo
from .mensagem_conversa import MensagemConversa
from .module import Module
from .motivo_cancelamento import MotivoCancelamento
from .movimentacao_estoque import MovimentacaoEstoque
from .movimento_caixa import MovimentoCaixa
from .nfe_entrada import NfeDocumento, NfeItem  # noqa: F401
from .nfe_tentativa_envio import NFeTentativaEnvio
from .nfse import NfseCredential, NfseInvoice, NfseMessageLog, NfseProviderConfig, NfseRps
from .nota_certificado import NotaCertificado
from .nota_fiscal import NotaFiscal, NotaFiscalItem
from .nota_servico import NotaServico, NotaServicoItem
from .notificacao_lida import NotificacaoLida
from .orcamento import Orcamento, OrcamentoItem
from .ordem_servico import OrdemServico, OrdemServicoItem
from .ordem_servico_tipo import OrdemServicoTipo  # noqa: F401
from .password_reset_token import PasswordResetToken
from .payment import Payment
from .payment_log import PaymentLog

# Fase 3.3 Módulo de Pagamentos
from .payment_provider_config import PaymentProviderConfig
from .payment_transaction import PaymentTransaction
from .pedido import Pedido, PedidoFaturamento, PedidoHistorico, PedidoItem, ReservaEstoque
from .pedido_item_marketplace import PedidoItemMarketplace
from .pedido_marketplace import PedidoMarketplace
from .pedido_status_evento import PedidoStatusEvento
from .permissao import Permissao

# SaaS: tenants, plans, modules, entitlements
from .plan import Plan

# Fase 2 — Estrutura Comercial
from .preco_pdv import PrecoPdv

# Produtos por estabelecimento (Fase 2 - Plano Hierarquia)
from .produto_cliente import ProdutoCliente
from .produto_fornecedor import ProdutoFornecedor
from .refund import Refund
from .regra_fiscal_icms import RegraFiscalIcms, TipoDestinatarioFiscalEnum, TipoOperacaoFiscalEnum

# Repasses financeiros (plataforma → CA)
from .repasse import Repasse
from .repasse_status import RepasseStatus
from .report_definition import ReportDefinition

# Relatórios (E-Relatórios - catálogo e jobs assíncronos)
from .report_job import ReportArtifact, ReportJob
from .reserva_estoque_marketplace import ReservaEstoqueMarketplace
from .revisao_direcao import RevisaoDirecao

# Modelos RBAC (Role-Based Access Control)
from .role import Role
from .role_permissao import RolePermissao

# Fase 5.2 Senha mestra por estabelecimento
from .senha_mestra_estabelecimento import SenhaMestraEstabelecimento
from .split_rule import SplitRule
from .status_pedido_marketplace import StatusPedidoMarketplace
from .subscription_billing import ComissaoAdministrador, SubscriptionBilling
from .sync_controle import SyncControle
from .tenant import Tenant
from .tenant_entitlement import TenantEntitlement
from .termo_buscado import TermoBuscado
from .tipo_equipamento import TipoEquipamento
from .tipo_material import TipoMaterial
from .transaction_split import TransactionSplit
from .usuario import Usuario
from .venda import Venda, VendaItem
from .venda_pagamento import VendaPagamento
from .webhook_event import WebhookEvent
from .whatsapp_webhook_event import WhatsappWebhookEvent  # noqa: F401

__all__ = [
    # Modelos Principais
    "Cliente",
    "Usuario",
    "PasswordResetToken",
    "TipoEquipamento",
    "NotificacaoLida",

    # Modelos de Controle (3)
    "Assinatura",
    "NotaCertificado",
    "Configuracao",

    # Modelos de Alertas (2)
    "AlertaEmail",
    "AlertaEnviado",

    # Modelos Qualidade ISO 17025
    "AcaoCorretiva",
    "RevisaoDirecao",

    # Modelos do Cliente (2)
    "AreaCliente",
    "DownloadCliente",

    # Modelos RBAC
    "Role",
    "Permissao",
    "RolePermissao",
    "AdministradorCliente",
    "ClienteAdministradorCliente",
    "ClienteAdministradorTecnico",
    "AdministradorClienteAdministrador",

    # Modelos de Negócios (PDV, caixa, vendas)
    "MaterialCategoria",
    "TipoMaterial",
    "Caixa",
    "AberturaCaixa",
    "Venda",
    "VendaItem",
    "Orcamento",
    "OrcamentoItem",
    "Pedido",
    "PedidoItem",
    "PedidoFaturamento",
    "PedidoHistorico",
    "ReservaEstoque",
    "OrdemServico",
    "OrdemServicoItem",
    "ProdutoCliente",
    "CodigoBarrasCliente",
    "FornecedorCliente",
    "ProdutoFornecedor",
    "MovimentacaoEstoque",
    "EstabelecimentoFiscal",
    "VendaPagamento",
    "MovimentoCaixa",
    "SenhaMestraEstabelecimento",
    "PaymentProviderConfig",
    "SplitRule",
    "PaymentTransaction",
    "TransactionSplit",
    "PaymentLog",

    # Modelos Fiscais (13)
    "Empresa",
    "NotaFiscal",
    "NotaFiscalItem",
    "NotaServico",
    "NotaServicoItem",
    "CupomFiscal",
    "CupomFiscalItem",
    "MDFe",
    "MDFeDocumento",
    "MDFeVeiculo",
    "MDFeCondutor",
    "MDFePercurso",
    "FiscalEvento",
    "NFeTentativaEnvio",
    "FiscalDownloadLog",
    "RegraFiscalIcms",
    "TipoOperacaoFiscalEnum",
    "TipoDestinatarioFiscalEnum",
    "FiscalDocumento",
    "FiscalDocumentoEmitenteSnapshot",
    "FiscalDocumentoDestinatarioSnapshot",
    "FiscalDocumentoItem",
    "FiscalDocumentoItemImpostos",
    "FiscalDocumentoTotais",
    "FiscalDocumentoTransporte",
    "FiscalDocumentoDuplicata",
    "FiscalXmlStore",
    "FiscalEventoDocumento",
    "FiscalStatusDocumento",
    "FiscalTipoDocumento",
    "FiscalAmbiente",
    "FiscalTipoOperacao",
    "FiscalFinalidadeEmissao",
    "FiscalTipoXml",
    "FiscalTipoEvento",
    "NfseInvoice",
    "NfseRps",
    "NfseCredential",
    "NfseMessageLog",
    "NfseProviderConfig",
    "AuditLog",
    "AccessLog",
    "BillingEvent",
    "ReportJob",
    "ReportArtifact",
    "ReportDefinition",
    "Plan",
    "Module",
    "Tenant",
    "GoogleCseUsoLog",
    "TenantEntitlement",
    "SubscriptionBilling",
    "ComissaoAdministrador",
    "Payment",
    "WebhookEvent",
    "BillingNotificacao",

    # Fase 2 — Estrutura Comercial
    "PrecoPdv",
    "ContratoComercial",
    "ContratoAditivo",
    "Divulgador",
    "DivulgadorRegra",
    "CodigoDesconto",

    # Marketplace
    "LojaMarketplace",
    "LojaSlugHistory",
    "LojaAreaEntrega",
    "MarketingVitrineConfig",
    "MarketingVitrineCard",
    "CategoriaPlataforma",
    "ConsumidorMarketplace",
    "ConsumidorSocialIdentity",
    "ConsumidorSocialLinkPending",
    "EnderecoConsumidor",
    "AnuncioPlataforma",
    "SyncControle",
    "PedidoMarketplace",
    "PedidoItemMarketplace",
    "MarketplaceCheckoutSession",
    "MarketplaceCheckoutSessionPedido",
    "PedidoStatusEvento",
    "IntegrationEvent",
    "AvaliacaoMarketplace",
    "ExtratoLoja",
    "ReservaEstoqueMarketplace",
    "StatusPedidoMarketplace",
    "Refund",
    "BillingUsageEvent",
    # Modulo Influencers
    "InfluencerCampanha",
    "InfluencerLink",
    "InfluencerMetrica",
    "Repasse",
    "RepasseStatus",
    "Entregador",
    "EntregadorVeiculo",
    "EntregaMarketplace",
    "EntregaEvento",
    # Mobile App — Sprint 1
    "ConsumidorPushToken",
    "ConsumidorRefreshToken",
    "ConsumidorFavorito",
    "ConsumidorNotificacao",
    "AppVersaoConfig",
    # Mobile App — Sprint 2
    "CupomMarketplace",
    "CupomConsumidor",
    "MotivoCancelamento",
    "DevolucaoMarketplace",
    # Mobile App — Sprint 3
    "ConversaMarketplace",
    "MensagemConversa",
    "ConsumidorConsentimento",
    "TermoBuscado",
]
