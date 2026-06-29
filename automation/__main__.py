import sys

from automation.src.application.workflows import (
    enviar_assinatura,
    finalizar_proposta,
    gerar_proposta,
)
from automation.src.config import get_logger, setup_logging

setup_logging()
logger = get_logger("main")

if __name__ == "__main__":
    etapa = sys.argv[1] if len(sys.argv) > 1 else "proposta"

    if etapa == "proposta":
        logger.info("=== PIPELINE 1: Gerar Proposta ===")
        resultado = gerar_proposta.executar()
        if resultado:
            logger.info("PDF gerado: %s", resultado)
        else:
            logger.error("Falha ao gerar proposta.")

    elif etapa == "assinatura":
        logger.info("=== PIPELINE 2: Enviar para Assinatura ===")
        resultado = enviar_assinatura.executar()
        if resultado:
            logger.info("Link: %s", resultado)
        else:
            logger.error("Falha ao enviar para assinatura.")

    elif etapa == "finalizar":
        logger.info("=== PIPELINE 3: Finalizar Tarefa 04.1 no Triata ===")
        if finalizar_proposta.executar():
            logger.info("Tarefa finalizada com sucesso.")
        else:
            logger.error("Falha ao finalizar tarefa.")

    elif etapa == "completo":
        logger.info("=== PIPELINE COMPLETA ===")
        pdf = gerar_proposta.executar()
        if not pdf:
            logger.error("Falha na etapa 1 (proposta).")
        else:
            logger.info("PDF gerado: %s", pdf)
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
        print("Uso: python -m automation [proposta|assinatura|finalizar|completo]")
