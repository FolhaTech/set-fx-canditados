from typing import Any

from automation.src.domain.models import Address, Proposal, Candidate, Enterprise
from automation.src.domain.validators import clean_checkbox, clean_value, is_checked


def extract_checked_items(dados: dict[str, Any], grupo: str) -> list[str]:
    itens: list[str] = []
    valores = dados.get(grupo, {})

    if isinstance(valores, dict):
        for _, valor in valores.items():
            if is_checked(valor):
                item = clean_checkbox(valor)
                if item:
                    itens.append(item)

    return itens


def build_address(dados: dict[str, Any]) -> Address:
    return Address(
        logradouro=clean_value(dados.get("endereco_completo")),
        numero=clean_value(dados.get("numero_endereco")),
        complemento=clean_value(dados.get("complemento_endereco")),
        bairro=clean_value(dados.get("bairro_prestador")),
        cidade=clean_value(dados.get("cidade_prestador")),
        cep=clean_value(dados.get("cep_prestador")),
    )


def build_candidate(dados: dict[str, Any]) -> Candidate:
    return Candidate(
        nome_completo=clean_value(dados.get("nome_completo")) or "Candidato",
        email=clean_value(dados.get("email_pessoal_candidato")) or None,
        cpf=clean_value(dados.get("cpf_candidato")) or None,
        rg=clean_value(dados.get("rg_candidato")) or None,
        data_nascimento=clean_value(dados.get("data_nascimento")) or None,
        estado_civil=clean_value(dados.get("estado_civil")) or None,
        celular=clean_value(dados.get("celular_candidato")) or None,
        endereco=build_address(dados),
    )


def parse_honorario(dados: dict[str, Any]) -> float | None:
    raw = clean_value(dados.get("honorario_novo_colaborador"))
    if not raw:
        return None
    try:
        return float(raw.replace(".", "").replace(",", "."))
    except (ValueError, TypeError):
        return None


def resolve_empresa(dados: dict[str, Any]) -> Enterprise:
    empresa_raw = (
            clean_value(dados.get("empresa_colaborador_novo"))
            or clean_value(dados.get("empresa_solicitante"))
    )
    return Enterprise.from_string(empresa_raw)


def build_proposal(dados: dict[str, Any]) -> Proposal:
    candidato = build_candidate(dados)
    empresa = resolve_empresa(dados)

    return Proposal(
        candidato=candidato,
        empresa=empresa,
        empresa_solicitante=clean_value(dados.get("empresa_solicitante")),
        honorario=parse_honorario(dados),
        tipo_vaga=clean_value(dados.get("tipo_vaga")),
        centro_custo=clean_value(dados.get("centro_custo")),
        funcionario_substituicao=clean_value(dados.get("funcionario_substituicao")),
        equipamentos=extract_checked_items(dados, "equipamentos"),
        sistemas=extract_checked_items(dados, "sistemas"),
        nome_responsavel=clean_value(dados.get("nome_responsavel_legal")),
        email_responsavel=clean_value(dados.get("email_responsavel_legal")),
        processo_id=clean_value(dados.get("processo_id")) or None,
        tarefa_nome=clean_value(dados.get("tarefa_nome")) or None,
        modelo_nome=clean_value(dados.get("modelo_nome")) or None,
    )
