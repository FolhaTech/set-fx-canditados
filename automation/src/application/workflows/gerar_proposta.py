import logging
import re
from datetime import datetime
from pathlib import Path

from automation.src.application.services.branding_service import find_logo
from automation.src.application.services.proposta_service import build_proposal
from automation.src.config import settings
from automation.src.domain import Enterprise, clean_value
from automation.src.domain.exceptions import TarefaNotFoundError
from automation.src.domain.validators import clean_filename
from automation.src.infrastructure.browser.factory import create_page
from automation.src.infrastructure.external_apis.triata_client import TriataClient
from automation.src.infrastructure.pdf.generator import (
    generate_contract_html,
    generate_proposal_pdf,
)
from automation.src.infrastructure.storage import (
    append_excel,
    candidate_exists,
    save,
    save_candidate,
)

logger = logging.getLogger("automacao.workflow.gerar_proposta")


def _voltar_para_lista(client: TriataClient) -> None:
    """Heurística Y: garante que estamos na lista de tarefas.

    1. Espera 5s pelo seletor da lista reaparecer (Triata volta sozinho).
    2. Se não aparecer, faz page.go_back() e espera mais 10s.
    """
    lista_selector = 'td[id^="tarefa_"]'
    try:
        client.page.wait_for_selector(lista_selector, timeout=5_000)
        return
    except Exception:
        pass

    logger.info("Lista não reapareceu — tentando go_back()")
    try:
        client.page.go_back()
        client.page.wait_for_selector(lista_selector, timeout=10_000)
    except Exception as e:
        logger.warning("Não consegui voltar para lista: %s", e)


def _gerar_pdf(dados: dict, processo_id: str, page_context) -> str | None:
    """Gera o PDF (carta proposta ou contrato). Retorna path ou None."""
    nome = clean_filename(dados.get("nome_completo", ""))
    tarefa = (dados.get("tarefa_nome") or "").lower()
    titulo_html = tarefa

    if "04.1" in tarefa or "05.1" in tarefa:
        output = settings.pdf_dir_path / f"Carta_Proposta_{nome}_{processo_id}.pdf"
        proposta = build_proposal(dados)
        generate_proposal_pdf(proposta, output)
        return str(output)

    if "08" in tarefa:
        template_path = settings.template_contrato_30_html_path
        output = settings.pdf_dir_path / f"Contrato_{nome}_{processo_id}.pdf"
        dados["data_atual"] = datetime.now().strftime("%d/%m/%Y")
        dados["endereco_formatado"] = (
            f"{dados.get('endereco_completo', '')}, "
            f"{dados.get('numero_endereco', '')} "
            f"{dados.get('complemento_endereco', '')} - "
            f"{dados.get('bairro_prestador', '')}"
        )
        dados["cidade_estado"] = f"{dados.get('cidade_prestador', '')}/SP"

        valor_raw = float(dados.get("honorario_novo_colaborador", "0"))
        valor_int = int(valor_raw)
        centavos = int(round((valor_raw - valor_int) * 100))
        valor_formatado = f"R$ {valor_int:,}".replace(",", ".")
        valor_formatado += f",{centavos:02d}" if centavos else ",00"
        dados["valor_remuneracao"] = valor_formatado

        empresa = Enterprise.from_string(
            clean_value(
                dados.get("empresa_novo_colaborador")
                or clean_value(dados.get("empresa_solicitante"))
            )
        )
        logo_empresa = find_logo(empresa)

        resultado = generate_contract_html(
            dados=dados,
            output_path=output,
            template_path=template_path,
            context=page_context,
            logo_path=logo_empresa,
        )
        return str(output) if resultado else None

    return None


def _processar_tarefa(client: TriataClient, tarefa, idx: int, total: int) -> str | None:
    """Processa uma tarefa individual. Retorna path do PDF ou None."""

    title = (tarefa.get_attribute("title") or "").strip()
    tarefa_id = tarefa.get_attribute("id") or ""

    match = re.search(r"tarefa_(\d+)_\d+", tarefa_id)
    if not match:
        logger.warning("[%d/%d] Tarefa sem processo_id (id=%s)", idx, total, tarefa_id)
        return None
    processo_id = match.group(1)

    if candidate_exists(processo_id):
        logger.info(
            "[%d/%d] Processo %s já processado — pulando", idx, total, processo_id
        )
        return None

    logger.info("[%d/%d] %s (processo %s)", idx, total, title, processo_id)

    client.page.on("dialog", lambda dialog: dialog.accept())
    tarefa.click()

    try:
        dados = client.extract_form()
    except Exception as e:
        logger.error("[%d/%d] Falha ao extrair: %s", idx, total, e)
        return None

    dados["tarefa_nome"] = title
    dados["processo_id"] = processo_id

    nome = dados.get("nome_completo", "")
    pdf_path = _gerar_pdf(dados, processo_id, client.page.context)

    if pdf_path:
        save_candidate(processo_id, nome, dados)
        save(settings.json_path, dados)
        append_excel(settings.excel_path, dados)
        logger.info("[%d/%d] OK: %s", idx, total, Path(pdf_path).name)

    _voltar_para_lista(client)
    return pdf_path


def executar() -> list[str]:
    """Processa a fila inteira de candidatos no Triata.

    Returns:
        Lista de paths de PDFs gerados nesta execução.
    """
    page, browser, playwright = create_page()
    pdfs: list[str] = []

    try:
        client = TriataClient(
            page=page,
            url=settings.TRIATA_URL,
            username=settings.TRIATA_USERNAME,
            password=settings.TRIATA_PASSWORD,
        )
        client.login()
        client.ativar_modo_teste()

        try:
            tarefas = client.find_all_tasks()
        except TarefaNotFoundError:
            logger.info("Nenhuma tarefa de confecção na fila.")
            return []

        total = len(tarefas)
        sucessos = pulados = falhas = 0

        for idx, tarefa in enumerate(tarefas, start=1):
            try:
                pdf_path = _processar_tarefa(client, tarefa, idx, total)
                if pdf_path:
                    pdfs.append(pdf_path)
                    sucessos += 1
                else:
                    pulados += 1
            except Exception as e:
                falhas += 1
                logger.error("[%d/%d] Erro inesperado: %s", idx, total, e)
                logger.exception("Traceback:")

        logger.info(
            "Resumo: %d processados, %d pulados, %d falhas (de %d)",
            sucessos,
            pulados,
            falhas,
            total,
        )
        return pdfs

    except Exception:
        logger.exception("Erro no fluxo de fila.")
        return pdfs

    finally:
        try:
            page.context.browser.close()
        except Exception:
            pass
        playwright.stop()
