import logging

from playwright.sync_api import Page
import httpx

from automation.src.config import settings
from automation.src.domain.exceptions import (
    ZapSignLinkError,
    ZapSignUploadError,
)
from automation.src.infrastructure.browser.actions import (
    click_canvas_center,
    close_modal,
    safe_click,
    safe_fill,
    scroll_viewer_to_bottom,
    wait_for_spinners,
    wait_for_value,
)

logger = logging.getLogger("automacao.zapsign")


class ZapSignClient:
    """Automação do ZapSign via Playwright."""

    def __init__(self, page: Page, url: str, email: str, senha: str):
        self.page = page
        self.url = url
        self.email = email
        self.senha = senha

    def login(self) -> None:
        """Login em 2 etapas: email → Entrar → senha → Entrar."""
        logger.info("Acessando ZapSign...")
        self.page.goto(self.url, wait_until="domcontentloaded")
        close_modal(self.page)

        logger.info("Etapa 1: Email")
        safe_fill(
            self.page,
            'input[inputmode="email"], input[placeholder*="e-mail"]',
            self.email,
        )
        self.page.locator("button:has-text('Entrar')").first.click()

        logger.info("Etapa 2: Senha")
        campo_senha = self.page.locator('input[type="password"]')
        campo_senha.wait_for(state="visible", timeout=20_000)
        campo_senha.fill(self.senha)
        self.page.locator("button:has-text('Entrar')").last.click()

        self.page.wait_for_selector("#button-create-doc-sidebar-test", timeout=40_000)
        close_modal(self.page)
        logger.info("Login ZapSign confirmado.")

    def navigate_to_contracts_robo(self) -> None:
        logger.info("Navegando para a página de contratos do Robo...")

        safe_click(
            self.page,
            '[data-cy="documentos"]',
            label="Documentos (sidebar)",
        )
        self.page.wait_for_load_state("domcontentloaded", timeout=30_000)

        safe_click(
            self.page,
            "body > app-root > div > app-client > div > div > app-sidebar > div "
            "> div.zs-two-blocks-sidebar > div:nth-child(1) > ul "
            "> div:nth-child(1) > li",
            label="Documentos Criados",
        )
        self.page.wait_for_load_state("domcontentloaded", timeout=30_000)

        safe_click(
            self.page,
            "body > app-root > div > app-client > div > div > div "
            "> app-my-documents > app-documents > div > div "
            "> div.container-folders-doc.ng-star-inserted > app-folders > div "
            "> div > div > app-folder-tree > div > div > div.folders-list "
            "> app-folder:nth-child(2) > div",
            label="Pasta Contratos Robo",
        )
        self.page.wait_for_load_state("domcontentloaded", timeout=30_000)

        safe_click(
            self.page,
            "body > app-root > div > app-client > div > div > div "
            "> app-my-documents > app-documents > div > div "
            "> div.container-folders-doc.ng-star-inserted > div > app-accordion "
            "> div > div.container-btn > zs-button:nth-child(1) > button "
            "> span.mat-button-wrapper",
            label="Criar documento (na pasta)",
        )
        self.page.wait_for_load_state("domcontentloaded", timeout=30_000)
        logger.info("Pronto para upload na pasta Contratos Robo.")

    def create_and_upload(self, pdf_paths: list[str]) -> None:
        """Cria novo documento e faz upload dos PDFs."""
        logger.info("Criando documento...")
        safe_click(self.page, "#button-create-doc-sidebar-test", label="Criar doc")

        logger.info("Aguardando input de upload...")
        file_input = self.page.locator('input#files[type="file"]')
        file_input.wait_for(state="attached", timeout=30_000)

        logger.info("Enviando PDFs: %s", pdf_paths)
        file_input.set_input_files(pdf_paths)

        logger.info("Aguardando processamento...")
        wait_for_spinners(self.page)

        logger.info("Clicando Continuar...")
        safe_click(self.page, '[data-cy="continuarBtn"]', label="Continuar upload")
        self.page.wait_for_load_state("domcontentloaded")
        close_modal(self.page)

    def enable_advanced_auth(self) -> None:
        """Ativa o toggle de autenticação avançada."""
        logger.info("Ativando autenticação avançada...")
        toggle = self.page.locator("#toggle-authentication-test-id-input")
        toggle.wait_for(state="visible", timeout=30_000)

        if toggle.get_attribute("aria-checked") != "true":
            close_modal(self.page)
            self.page.locator(
                'label[for="toggle-authentication-test-id-input"]'
            ).click()
            self.page.wait_for_timeout(300)
            self.page.wait_for_function(
                """() => document.querySelector(
                    '#toggle-authentication-test-id-input'
                )?.getAttribute('aria-checked') === 'true'""",
                timeout=15_000,
            )
        logger.info("Autenticação avançada ativada.")

    def fill_signer_info(self, nome: str, email: str | None = None) -> None:
        """Preenche nome e email do signatário."""
        logger.info("Preenchendo signatário: %s", nome)
        safe_fill(self.page, "#signer-name-field-test-id", nome)
        wait_for_value(
            self.page,
            "#signer-name-field-test-id",
            "el.value.trim().length > 0",
        )

        if email:
            safe_fill(self.page, "#signer-email-field-test-id", email)
            wait_for_value(
                self.page,
                "#signer-email-field-test-id",
                "el.value.includes('@')",
            )

        logger.info("Signatário preenchido.")

    def send_document(self) -> None:
        """Clica no botão final de envio."""
        logger.info("Clicando em Enviar...")
        safe_click(
            self.page,
            "#send-document-button-test",
            label="Enviar documento",
        )
        self.page.wait_for_load_state("domcontentloaded")
        close_modal(self.page)
        logger.info("Documento enviado.")

    def apply_verification_marks(self) -> None:
        """Aplica visto em todas as páginas do PDF viewer."""
        logger.info("Aguardando viewer do PDF...")
        self.page.wait_for_selector(
            "app-pdf-viewer .page[data-page-number]", timeout=180_000
        )
        self.page.wait_for_selector(
            "app-pdf-viewer .page[data-page-number] canvas", timeout=180_000
        )

        paginas = self.page.locator("app-pdf-viewer .page[data-page-number]")
        total = paginas.count()

        if total == 0:
            raise ZapSignUploadError("Nenhuma página no viewer.")

        logger.info("Total de páginas: %d", total)

        for i in range(total):
            close_modal(self.page, timeout_ms=500)

            pagina = paginas.nth(i)
            num = pagina.get_attribute("data-page-number") or str(i + 1)
            pagina.scroll_into_view_if_needed()
            self.page.wait_for_timeout(200)

            canvas = pagina.locator("canvas").first
            if not click_canvas_center(self.page, canvas, label=f"pg{num}"):
                raise ZapSignUploadError(
                    f"Bounding box do canvas não encontrada na página {num}."
                )

            # Seleciona opção "Visto"
            visto = self.page.locator("#zs-options-lines-visto")
            visto.wait_for(state="visible", timeout=30_000)
            safe_click(self.page, "#zs-options-lines-visto", label=f"Visto pg{num}")

            logger.info("Visto aplicado na página %s", num)
            self.page.wait_for_timeout(250)

    def place_signature_field(self) -> None:
        """Insere campo de assinatura na última página de cada viewer."""
        self.page.wait_for_selector(".pdfViewer", timeout=90_000)
        self.page.wait_for_selector(
            ".pdfViewer .page[data-page-number]", timeout=90_000
        )
        self.page.wait_for_selector(
            ".pdfViewer .page[data-page-number] canvas", timeout=90_000
        )

        viewers = self.page.locator(".pdfViewer")
        total = viewers.count()

        if total == 0:
            # Fallback: páginas globais
            logger.warning("pdfViewer não encontrado. Fallback global.")
            pages = self.page.locator(".page[data-page-number]")
            cnt = pages.count()
            if cnt == 0:
                raise ZapSignUploadError("Nenhuma página para assinatura.")

            idxs = [cnt - 1, cnt - 2] if cnt >= 2 else [cnt - 1]
            for pidx in idxs:
                pg = pages.nth(pidx)
                canvas = pg.locator("canvas").first
                if click_canvas_center(self.page, canvas, label="global"):
                    safe_click(
                        self.page, "#zs-options-lines-signature", label="Ass global"
                    )
                    return
            return

        logger.info("Viewers encontrados: %d", total)

        for idx in range(total):
            close_modal(self.page, timeout_ms=500)
            viewer = viewers.nth(idx)
            logger.info("Processando viewer %d/%d", idx + 1, total)

            scroll_viewer_to_bottom(self.page, viewer)

            pages = viewer.locator(".page[data-page-number]")
            cnt = pages.count()
            if cnt == 0:
                continue

            cand_idxs = [cnt - 1]
            if cnt >= 2:
                cand_idxs.append(cnt - 2)

            for pidx in cand_idxs:
                pg = pages.nth(pidx)
                canvas = pg.locator("canvas").first
                if click_canvas_center(self.page, canvas, label=f"v{idx + 1}"):
                    safe_click(
                        self.page,
                        "#zs-options-lines-signature",
                        label=f"Ass v{idx + 1}",
                    )
                    logger.info("Assinatura inserida no viewer %d", idx + 1)
                    break

    def save_and_continue(self) -> None:
        """Clica em Salvar e continuar."""
        safe_click(
            self.page,
            "#save-and-continue-btn-test",
            label="Salvar e continuar",
        )
        self.page.wait_for_load_state("domcontentloaded")

    def capture_link(self) -> str:
        """Aguarda e captura o link de assinatura."""
        logger.info("Aguardando link de assinatura...")
        self.page.wait_for_function(
            """() => {
                const el = document.querySelector('input.signer_link');
                return el && el.value && el.value.startsWith('http');
            }""",
            timeout=120_000,
        )

        campo = self.page.locator("input.signer_link")
        link = campo.input_value()

        if not link.startswith("http"):
            raise ZapSignLinkError(f"Link inválido: {link}")

        logger.info("Link capturado: %s", link)
        return link

    def run_full_workflow(
        self, nome: str, email: str | None, pdf_paths: list[str]
    ) -> str:
        """Executa o fluxo completo e retorna o link de assinatura."""
        self.login()
        self.navigate_to_contracts_robo()
        self.create_and_upload(pdf_paths)
        self.enable_advanced_auth()
        self.fill_signer_info(nome, email)
        self.send_document()
        self.apply_verification_marks()
        self.place_signature_field()
        self.save_and_continue()
        link = self.capture_link()

        return link
