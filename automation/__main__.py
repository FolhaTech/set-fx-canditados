import sys

from automation.src.application.workflows import (
    enviar_assinatura,
    finalizar_proposta,
    gerar_proposta,
    processar_fila,
)
from automation.src.config import get_logger, setup_logging

setup_logging()
logger = get_logger("main")

if __name__ == "__main__":
    etapa = sys.argv[1] if len(sys.argv) > 1 else "proposta"

    if etapa == "proposta":
        logger.info("=== PIPELINE 1: Gerar Proposta (fila) ===")
        resultado = gerar_proposta.executar()
        if resultado:
            logger.info("%d PDFs gerados nesta execução:", len(resultado))
            for p in resultado:
                logger.info("  - %s", p)
        else:
            logger.warning("Nenhum PDF gerado (fila vazia ou tudo já processado).")

    elif etapa == "assinatura":
        logger.info("=== PIPELINE 2: Enviar para Assinatura (último) ===")
        resultado = enviar_assinatura.executar()
        if resultado:
            logger.info("Link: %s", resultado)
        else:
            logger.error("Falha ao enviar para assinatura.")

    elif etapa == "finalizar":
        logger.info("=== PIPELINE 3: Finalizar Tarefa 04.1 no Triata (último) ===")
        if finalizar_proposta.executar():
            logger.info("Tarefa finalizada com sucesso.")
        else:
            logger.error("Falha ao finalizar tarefa.")

    elif etapa == "processar":
        logger.info("=== PIPELINE COMPLETA (fila inteira) ===")
        if processar_fila.executar():
            logger.info("Fila processada com sucesso.")
        else:
            logger.error("Fila processada com falhas (ver log).")

    elif etapa == "completo":
        logger.info("=== PIPELINE COMPLETA (1 candidato por vez) ===")
        pdfs = gerar_proposta.executar()
        if not pdfs:
            logger.warning("Fila vazia ou tudo já processado. Encerrando sem enviar assinatura.")
        else:
            logger.info("%d PDFs gerados.", len(pdfs))
            link = enviar_assinatura.executar()
            if not link:
                logger.error("Falha na etapa 2 (assinatura).")
            else:
                logger.info("Link: %s", link)
                if not finalizar_proposta.executar():
                    logger.error("Falha na etapa 3 (finalizar).")
                else:
                    logger.info("Pipeline completa finalizada.")

    else:
        print("Uso: python -m automation [proposta|assinatura|finalizar|processar|completo]")
