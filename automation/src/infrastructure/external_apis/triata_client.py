import logging
import re

from playwright.sync_api import Page

from automation.src.domain.exceptions import (
    TarefaNotFoundError,
    TriataLoginError,
)
from automation.src.infrastructure.browser.actions import safe_click, safe_fill

logger = logging.getLogger("automacao.triata")


class TriataClient:
    """Automação do sistema Triata via Playwright."""

    def __init__(self, page: Page, url: str, username: str, password: str):
        self.page = page
        self.url = url
        self.username = username
        self.password = password

    def login(self) -> None:
        """Acessa a URL e faz login com usuário e senha."""
        logger.info("Acessando Triata...")
        self.page.goto(self.url, wait_until="domcontentloaded", timeout=40_000)
        self.page.wait_for_load_state("networkidle", timeout=30_000)

        logger.info("Preenchendo login...")
        safe_fill(self.page, 'input[name="login"]', self.username)

        logger.info("Preenchendo senha...")
        safe_fill(self.page, 'input[name="senha"]', self.password)

        logger.info("Clicando em Entrar...")
        safe_click(self.page, "#TriataBtAcessar", label="Login Triata")

        # Confirma que o login sumiu
        try:
            self.page.wait_for_selector('input[name="login"]', state="hidden", timeout=30_000)
            logger.info("Login realizado. URL: %s", self.page.url)
        except Exception:
            raise TriataLoginError("Campo de login ainda visível após tentativa.")

    def ativar_modo_teste(self) -> None:
        """Clica no botão Modo Teste e aceita o diálogo de confirmação."""
        logger.info("Ativando Modo Teste...")
        self.page.on("dialog", lambda dialog: dialog.accept())

        self.page.wait_for_timeout(5_000)

        clicado = False

        btn = self.page.locator(".btn_ativa_modo_teste")
        try:
            btn.wait_for(state="attached", timeout=10_000)
            btn.click()
            clicado = True
            logger.info("Modo Teste clicado na página principal.")
        except Exception:
            pass

        if not clicado:
            logger.info("Botão não encontrado. Chamando ModoTeste('I') via JavaScript...")
            try:
                self.page.evaluate("""
                    () => {
                        if (typeof ModoTeste === 'function') {
                            ModoTeste('I');
                        } else {
                            // Procurar o botão no DOM e clicar via JS
                            const btn = document.querySelector('.btn_ativa_modo_teste');
                            if (btn) btn.click();
                        }
                    }
                """)
                clicado = True
                logger.info("ModoTeste('I') chamado via JS.")
            except Exception as e:
                logger.warning("Falha ao ativar via JS: %s", e)

        if not clicado:
            logger.warning("Não foi possível ativar Modo Teste.")

        self.page.wait_for_load_state("networkidle", timeout=30_000)
        self.page.wait_for_timeout(3_000)
        self.page.wait_for_selector('td[id^="tarefa_"]', timeout=20_000)
        logger.info("Modo Teste processado.")

    def find_task(self) -> tuple[str, str]:
        """Encontra e clica na primeira tarefa de confecção.

        Returns:
            (nome_tarefa, processo_id) — ex: ("04.1 - Confecção Proposta", "12345")
        """
        logger.info("Aguardando listagem de tarefas...")
        self.page.wait_for_selector('td[id^="tarefa_"]', timeout=20_000)

        tds = self.page.locator('td[id^="tarefa_"]').all()
        logger.info("Encontradas %d tarefas.", len(tds))

        if not tds:
            raise TarefaNotFoundError("Nenhuma tarefa na listagem.")

        primeiro = tds[0]
        titulo = primeiro.get_attribute("title")
        id_td = primeiro.get_attribute("id")

        if not titulo or not id_td:
            raise TarefaNotFoundError("Primeira tarefa sem title ou id.")

        titulo_lower = titulo.strip().lower()
        if "04.1" in titulo_lower:
            nome_tarefa = "04.1 - Confecção Proposta"
        elif "08" in titulo_lower:
            nome_tarefa = "08 - Confecção e assinatura (Contrato)"
        else:
            raise TarefaNotFoundError(f"Tarefa não é de confecção: {titulo}")

        match = re.search(r"tarefa_(\d+)_\d+", id_td)
        if not match:
            raise TarefaNotFoundError(f"Não extraiu processo_id de: {id_td}")
        processo_id = match.group(1)

        logger.info("Tarefa: %s | Processo: %s", nome_tarefa, processo_id)

        self.page.on("dialog", lambda dialog: dialog.accept())
        primeiro.click()

        try:
            self.page.wait_for_selector("#TriareProcessoForm", timeout=20_000)
            logger.info("Formulário carregado.")
        except Exception:
            raise TarefaNotFoundError("Formulário #TriareProcessoForm não carregou.")

        return nome_tarefa, processo_id

    def extract_form(self) -> dict:
        logger.info("Extraindo campos do formulário...")
        self.page.wait_for_selector("#TriareProcessoForm", timeout=20_000)

        dados = self.page.evaluate("""
            () => {
                const form = document.querySelector("#TriareProcessoForm");
                const data = {
                    extraido_em: new Date().toLocaleString("pt-BR"),
                    url: window.location.href
                };
                const elements = form.querySelectorAll("input, select, textarea");
                elements.forEach(el => {
                    const key = el.id || el.name;
                    if (!key) return;
                    if (el.type === 'checkbox' || el.type === 'radio') {
                        data[key] = el.checked ? (el.value || true) : false;
                    } else if (el.tagName === 'SELECT') {
                        data[key] = el.options[el.selectedIndex]
                            ? el.options[el.selectedIndex].text.trim() : "";
                    } else {
                        data[key] = el.value || "";
                    }
                });
                return data;
            }
        """)

        logger.info("Total de %d campos extraídos.", len(dados))
        return dados

    def run(self) -> dict | None:
        try:
            self.login()
            self.ativar_modo_teste()
            nome_tarefa, processo_id = self.find_task()
            dados = self.extract_form()

            dados["tarefa_nome"] = nome_tarefa
            dados["processo_id"] = processo_id

            return dados
        except Exception:
            logger.exception("Erro no fluxo Triata.")
            return None
