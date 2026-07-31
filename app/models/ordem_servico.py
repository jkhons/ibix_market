from sqlalchemy import DECIMAL, Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database.base import BaseModel


class OrdemServico(BaseModel):
    __tablename__ = "ordem_servico"

    codigo = Column(String(30), nullable=False, unique=True, index=True)

    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False)
    responsavel_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    tipo_id = Column(
        Integer,
        ForeignKey("ordem_servico_tipo.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    prioridade = Column(
        Enum("baixa", "media", "alta", "critica", name="ordem_servico_prioridade_enum", native_enum=False),
        nullable=False,
        default="media",
    )

    status = Column(
        Enum(
            "aberta",
            "em_andamento",
            "aguardando_material",
            "aguardando_cliente",
            "concluida",
            "cancelada",
            name="ordem_servico_status_enum",
            native_enum=False,
        ),
        nullable=False,
        default="aberta",
        index=True,
    )

    data_abertura = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    data_prevista = Column(DateTime(timezone=True), nullable=True)
    data_conclusao = Column(DateTime(timezone=True), nullable=True)

    observacoes = Column(Text, nullable=True)

    orcamento_origem_id = Column(
        Integer,
        ForeignKey("orcamentos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Orçamento que originou esta OS (conversão Orç→OS)",
    )

    empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="SET NULL"), nullable=True, index=True, comment="Emissor da NFS-e ao faturar a OS")

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="ordens_servico")
    tipo_rel = relationship("OrdemServicoTipo", backref="ordens_servico", foreign_keys=[tipo_id])
    empresa = relationship("Empresa", backref="ordens_servico_emitidas", foreign_keys=[empresa_id])
    responsavel = relationship("Usuario", back_populates="ordens_servico_responsavel", foreign_keys=[responsavel_id])
    itens = relationship(
        "OrdemServicoItem",
        back_populates="ordem_servico",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    notas_servico = relationship(
        "NotaServico",
        back_populates="ordem_servico",
        lazy="selectin",
    )
    vendas = relationship(
        "Venda",
        back_populates="ordem_servico",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<OrdemServico(id={self.id}, codigo='{self.codigo}', status='{self.status}')>"


class OrdemServicoItem(BaseModel):
    __tablename__ = "ordem_servico_itens"

    ordem_servico_id = Column(
        Integer,
        ForeignKey("ordem_servico.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    produto_cliente_id = Column(
        Integer,
        ForeignKey("produtos_cliente.id", ondelete="SET NULL"),
        nullable=True,
    )

    codigo = Column(String(50), nullable=True)
    nome = Column(String(255), nullable=False)
    unidade = Column(String(20), nullable=True)

    quantidade = Column(DECIMAL(10, 2), nullable=False, default=0)
    valor_unitario = Column(DECIMAL(10, 2), nullable=False, default=0)
    desconto = Column(DECIMAL(10, 2), nullable=False, default=0)
    valor_total = Column(DECIMAL(10, 2), nullable=False, default=0)

    observacao = Column(Text, nullable=True)

    ordem_servico = relationship("OrdemServico", back_populates="itens")
    produto_cliente = relationship("ProdutoCliente", foreign_keys=[produto_cliente_id])

    def __repr__(self) -> str:
        return (
            f"<OrdemServicoItem(id={self.id}, ordem_servico_id={self.ordem_servico_id}, "
            f"nome='{self.nome}', quantidade={self.quantidade}, valor_total={self.valor_total})>"
        )

