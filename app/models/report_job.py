# PDV Ibix - Report Job (E-Relatórios)
# Jobs de geração de relatórios assíncronos. Escopo por cliente_id (ClienteScope).
import uuid

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import Base


class ReportJob(Base):
    """Job de geração de relatório (fila assíncrona)."""
    __tablename__ = "report_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    report_key = Column(String(128), nullable=False, index=True)
    output_format = Column(String(32), nullable=False)
    params_json = Column(JSONB, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="PENDING")
    progress = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    artifacts = relationship("ReportArtifact", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ReportJob(id={self.id}, report_key='{self.report_key}', status='{self.status}')>"


class ReportArtifact(Base):
    """Arquivo gerado por um report_job."""
    __tablename__ = "report_artifacts"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("report_jobs.id", ondelete="CASCADE"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    checksum_sha256 = Column(String(64), nullable=True)
    storage_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("ReportJob", back_populates="artifacts")

    def __repr__(self):
        return f"<ReportArtifact(id={self.id}, filename='{self.filename}')>"
