from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Enterprise(Enum):
    FOLHA_TECH = "Folha Tech"
    GENTER = "Genter"
    ARANTES = "Arantes"

    @classmethod
    def from_string(cls, name: str):
        name = (name or "").strip().lower()
        if "folha" in name and "tech" in name:
            return cls.FOLHA_TECH
        if "arantes" in name or "aaa" in name:
            return cls.ARANTES
        if "genter" in name:
            return cls.GENTER
        return cls.GENTER


@dataclass
class Address:
    logradouro: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    cidade: str = ""
    cep: str = ""

    @property
    def full_address(self) -> str:
        parts = [
            self.logradouro, self.numero, self.complemento, self.bairro, self.cidade, self.cep
        ]
        return " ".join(p for p in parts if p).strip()


@dataclass
class Candidate:
    nome_completo: str
    email: Optional[str] = None
    cpf: Optional[str] = None
    rg: Optional[str] = None
    data_nascimento: Optional[str] = None
    estado_civil: Optional[str] = None
    celular: Optional[str] = None
    endereco: Address = field(default_factory=Address)


@dataclass
class Proposal:
    candidato: Candidate
    empresa: Enterprise
    empresa_solicitante: str = ""
    honorario: Optional[float] = None
    tipo_vaga: str = ""
    centro_custo: str = ""
    funcionario_substituicao: str = ""
    equipamentos: list[str] = field(default_factory=list)
    sistemas: list[str] = field(default_factory=list)
    nome_responsavel: str = ""
    email_responsavel: str = ""

    # Process metadata
    processo_id: Optional[str] = None
    tarefa_nome: Optional[str] = None
    modelo_nome: Optional[str] = None


@dataclass
class Signature:
    link: str
    capturado_em: str = ""
    nome_signatario: str = ""
    email_signatario: Optional[str] = None
