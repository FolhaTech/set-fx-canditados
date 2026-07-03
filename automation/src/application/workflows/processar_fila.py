"""Orquestrador de fila completa (ZapSign + finalização).

Pré-requisito: `proposta` deve ter rodado antes (gera os PDFs e os
JSONs em `dados/<id>_<slug>.json`).

Para cada candidato na fila do Triata:
  1. Envia PDF para ZapSign (lê de dados/<id>_<slug>.json)
  2. Cola link no Triata e finaliza (lê de dados/<id>_<slug>.json)

Diferente do subcomando `completo`, este orquestrador processa
**N candidatos em sequência**, lendo os dados de cada um em
`dados/<id>_<slug>.json`.
"""

import logging

from automation.src.application.workflows import (
    enviar_assinatura,
    finalizar_proposta,
)
from automation.src.config import settings
from automation.src.infrastructure.browser.factory import create_page
from automation.src.infrastructure.external_apis.triata_client import TriataClient
from automation.src.infrastructure.storage import candidate_exists

logger = logging.getLogger("automacao.workflow.processar_fila")


def executar() -> bool:
    """Processa a fila completa do Triata: proposta + assinatura + finalização.

    Returns:
        True se TODOS os candidatos foram processados com sucesso.
    """
    page, browser, playwright = create_page()

    try:
        client = TriataClient(
            page=page,
            url=settings.TRIATA_URL,
            username=settings.TRIATA_USERNAME,
            password=settings.TRIATA_PASSWORD,
        )
        client.login()
        client.ativar_modo_teste()
        process_ids = client.list_process_ids()
    except Exception:
        logger.exception("Erro ao listar candidatos da fila do Triata.")
        return False
    finally:
        try:
            page.context.browser.close()
        except Exception:
            pass
        playwright.stop()

    if not process_ids:
        logger.info("Nenhum candidato de confecção na fila.")
        return True

    logger.info("Candidatos na fila: %d (%s)", len(process_ids), process_ids)

    sucessos: list[str] = []
    pulados: list[str] = []
    falhas: list[str] = []

    for processo_id in process_ids:
        if candidate_exists(processo_id):
            logger.info(
                "[%d/%d] Candidato %s já processado — pulando etapas 2 e 3",
                len(sucessos) + len(pulados) + len(falhas) + 1,
                len(process_ids),
                processo_id,
            )
            pulados.append(processo_id)
            continue

        logger.info(
            "[%d/%d] Processando candidato %s",
            len(sucessos) + len(pulados) + len(falhas) + 1,
            len(process_ids),
            processo_id,
        )

        link = enviar_assinatura.executar(processo_id=processo_id)
        if not link:
            logger.error("Falha no envio ZapSign para %s.", processo_id)
            falhas.append(processo_id)
            continue

        ok = finalizar_proposta.executar(processo_id=processo_id)
        if not ok:
            logger.error("Falha na finalização Triata para %s.", processo_id)
            falhas.append(processo_id)
            continue

        sucessos.append(processo_id)

    logger.info(
        "Resumo da fila: %d sucessos, %d pulados, %d falhas (de %d)",
        len(sucessos),
        len(pulados),
        len(falhas),
        len(process_ids),
    )
    if falhas:
        for pid in falhas:
            logger.error("  Falhou: %s", pid)

    return not falhas
