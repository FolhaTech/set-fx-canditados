from dataclasses import dataclass, field
from enum import Enum


class Enterprise(Enum):
    FOLHA_TECH = "folha_tech"
    GENTER = "genter"
    ARANTES = "arantes"

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
            self.logradouro,
            self.numero,
            self.complemento,
            self.bairro,
            self.cidade,
            self.cep,
        ]
        return " ".join(p for p in parts if p).strip()


@dataclass
class Candidate:
    nome_completo: str
    email: str | None = None
    cpf: str | None = None
    rg: str | None = None
    data_nascimento: str | None = None
    estado_civil: str | None = None
    celular: str | None = None
    endereco: Address = field(default_factory=Address)


@dataclass
class Proposal:
    candidato: Candidate
    empresa: Enterprise
    empresa_solicitante: str = ""
    honorario: float | None = None
    tipo_vaga: str = ""
    centro_custo: str = ""
    funcionario_substituicao: str = ""
    equipamentos: list[str] = field(default_factory=list)
    sistemas: list[str] = field(default_factory=list)
    nome_responsavel: str = ""
    email_responsavel: str = ""

    # Process metadata
    processo_id: str | None = None
    tarefa_nome: str | None = None
    modelo_nome: str | None = None


@dataclass
class Signature:
    link: str
    capturado_em: str = ""
    nome_signatario: str = ""
    email_signatario: str | None = None
