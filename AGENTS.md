# set-fx-candidatos

Automação de proposta e assinatura digital para candidatos via Playwright (sync API). Código-fonte em português.

## Comandos

```bash
uv run python -m automation proposta      # raspa Triata → JSON/Excel → PDF
uv run python -m automation assinatura    # envia PDF → ZapSign → link
uv run python -m automation completo      # proposta + assinatura em sequência
```

Sem argumento = `proposta`. Entrypoint: `automation/__main__.py`.

## Estrutura relevante

- `automation/src/infrastructure/browser/factory.py` — `create_page()` (Chromium, anti-detecção)
- `automation/src/infrastructure/external_apis/triata_client.py` — `TriataClient` (login → modo teste → find_task → extract_form)
- `automation/src/infrastructure/external_apis/zapsign_client.py` — `ZapSignClient` (login 2-etapas → upload → config → vistos → assinatura → link)
- `automation/src/infrastructure/pdf/generator.py` — geração de PDF (reportlab para carta proposta, HTML+Playwright para contrato)
- `automation/src/application/services/branding_service.py` — temas, logos, assinaturas por empresa
- `automation/src/domain/models.py` — `Enterprise` (enum lowercase: `folha_tech`, `genter`, `arantes`), `Candidate`, `Proposal`, `Address`, `Signature`

## Detalhes operacionais

- **Browser**: `HEADLESS=false`, `SLOW_MO=500ms`, viewport 1920x1080, locale pt-BR. Anti-detecção: `navigator.webdriver = undefined`, `--disable-blink-features=AutomationControlled`, user-agent Chrome 124.
- **Triata**: login fixo `robo.cadastro` / `Robo@aut2024` (settings.py). Pipeline: login → ativar modo teste `.btn_ativa_modo_teste` → clicar 1ª tarefa `td[id^="tarefa_"]` → extrair `#TriareProcessoForm` via JS. Tipos: "04.1" = carta proposta, "08" = contrato.
- **ZapSign**: credenciais via `.env` (`ZAPSIGN_EMAIL`, `ZAPSIGN_PASSWORD`). Login 2 etapas (email → "Entrar" → senha → "Entrar"). Upload → autenticação avançada → signatário → enviar → vistos em todas páginas → assinatura na última → capturar `input.signer_link`.
- **Timeouts**: default 30s, upload 3min, PDF viewer 90s, login 40s.
- **PDF tarefa "08"**: usa `modelo_contrato.html` + Playwright `page.pdf()` (não reportlab). Substitui `{{placeholders}}`, insere logo e assinaturas via base64. Template com rodapé fixo e CSS para A4.
- **Signature config**: `signatures.json` mapeia signatários por empresa/papel. Arquivos .svg em `signatures/`.
- **Logos**: diretório `logos/<empresa>/` (ex: `logos/arantes/logo-v2.png`). `branding_service.py` resolve por nome de arquivo predefinido.

## Dados

- `dados_formulario_atual.json` — sobrescrito a cada execução
- `dados_formularios.xlsx` — append histórico (planilha "Dados")
- `pdfs_gerados/` — PDFs gerados

## CI (`.github/workflows/ci.yml`)

Ubuntu + Python 3.12, apenas:

```bash
uv lock --check
uv sync --all-extras --dev
uv run python -c "import automation; print('Import OK')"
```

Lint/typecheck locais (não no CI):

```bash
uv run ruff check .              # line-length 100, double quotes, space indent, regras E/F/I/W/UP
uv run ruff format --check .
uv run mypy automation/            # strict=false, ignora reportlab.*, playwright.*, pandas.*, openpyxl.*, pydantic_settings.*
uv sync --all-extras --dev       # instalar dev deps
```
