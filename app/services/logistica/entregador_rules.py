# PDV Ibix — regras de habilitação do entregador (perfil + veículo aprovado)
from typing import Optional

from ...models import Entregador


def entregador_perfil_operacional(entregador: Entregador) -> bool:
    """Perfil aprovado pela plataforma e conta ativa."""
    return bool(entregador.ativo) and (entregador.status or "") == "ativo"


def entregador_tem_veiculo_aprovado_para_tipo(entregador: Entregador, tipo_veiculo_aceito: Optional[str]) -> bool:
    """
    tipo_veiculo_aceito na entrega: moto, carro, utilitario, qualquer ou None.
    Considera apenas veículos ativos com documento aprovado pelo Superadmin.
    """
    veics = [
        v
        for v in getattr(entregador, "veiculos", []) or []
        if v.ativo and v.documento_aprovado
    ]
    if not veics:
        return False
    t = (tipo_veiculo_aceito or "").strip().lower()
    if not t or t == "qualquer":
        return True
    for v in veics:
        vt = (v.tipo_veiculo or "").strip().lower()
        if vt == t:
            return True
    return False


def entregador_pode_operar_entregas(entregador: Entregador) -> bool:
    return entregador_perfil_operacional(entregador) and entregador_tem_veiculo_aprovado_para_tipo(entregador, "qualquer")
