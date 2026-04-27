# PDV Ibix - IStorage adapter (filesystem agora; S3 depois)
import hashlib
import os
from abc import ABC, abstractmethod
from typing import Optional


class IStorage(ABC):
    """Interface de armazenamento para PDFs de certificados. Filesystem agora; S3 depois."""

    @abstractmethod
    def save(self, rel_path: str, content: bytes, *, content_type: str = "application/pdf") -> str:
        """Salva conteudo em rel_path. Retorna path final (para leitura)."""
        ...

    @abstractmethod
    def load(self, rel_path: str) -> Optional[bytes]:
        """Carrega conteudo por path. Retorna None se nao existir."""
        ...

    @abstractmethod
    def exists(self, rel_path: str) -> bool:
        """Verifica se path existe."""
        ...

    @abstractmethod
    def delete(self, rel_path: str) -> bool:
        """Remove arquivo. Retorna True se removeu."""
        ...

    @abstractmethod
    def full_path(self, rel_path: str) -> str:
        """Retorna caminho absoluto (para FileResponse, etc.)."""
        ...


class FilesystemStorage(IStorage):
    """Implementacao filesystem. Base dir configurável (ex: app/static/docs/certificados_pdf)."""

    def __init__(self, base_dir: str = "app/static/docs/certificados_pdf"):
        self.base_dir = os.path.normpath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, rel_path: str) -> str:
        # Evitar path traversal
        if not rel_path or not rel_path.strip():
            raise ValueError("Path invalido")
        rel = os.path.normpath(rel_path.strip()).lstrip(os.sep)
        if rel.startswith("..") or os.path.isabs(rel_path):
            raise ValueError("Path invalido")
        return os.path.join(self.base_dir, rel)

    def save(self, rel_path: str, content: bytes, *, content_type: str = "application/pdf") -> str:
        p = self._path(rel_path)
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(p, "wb") as f:
            f.write(content)
        return rel_path

    def load(self, rel_path: str) -> Optional[bytes]:
        p = self._path(rel_path)
        if not os.path.isfile(p):
            return None
        with open(p, "rb") as f:
            return f.read()

    def exists(self, rel_path: str) -> bool:
        p = self._path(rel_path)
        return os.path.isfile(p)

    def delete(self, rel_path: str) -> bool:
        p = self._path(rel_path)
        if os.path.isfile(p):
            os.remove(p)
            return True
        return False

    def full_path(self, rel_path: str) -> str:
        return os.path.abspath(self._path(rel_path))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
