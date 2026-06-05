# set-fx-candidatos

Automação de proposta e assinatura digital para candidatos via Playwright. Código-fonte em português.

## Stack

- Python >=3.12, pacotes gerenciados com **uv** (vide `uv.lock`)
- **Playwright** (sync API) para automação de navegador
- **pydantic-settings** para config (carrega `.env` da raiz)
- **reportlab** para geração de PDF
- **pandas + openpyxl** para persistência em Excel

## Comandos

```bash
uv run python -m automation proposta      # gera PDF (raspa Triata → JSON/Excel → PDF)
uv run python -m automation assinatura    # envia PDF para assinatura ZapSign
uv run python -m automation completo      # proposta + assinatura em sequência
```

Sem argumento = `proposta`.

## Arquitetura

```
automation/__main__.py          → entrypoint (CLI dispatcher)
automation/src/
  config/settings.py            → Settings (lê .env, paths, timeouts)
  config/logging_config.py      → log format, supressão de libs ruidosas
  domain/
    models.py                   → Candidate, Proposal, Enterprise, Address
    validators.py               → normalize_text, clean_filename, format_currency
    exceptions.py               → hierarquia de exceções (Triata*, ZapSign*, PDF*)
  application/
    workflows/gerar_proposta.py → pipeline 1: Triata → dados → PDF
    workflows/enviar_assinatura.py → pipeline 2: PDF → ZapSign → link
    services/proposta_service.py   → montagem do modelo Proposal a partir do dict
  infrastructure/
    browser/factory.py          → create_page() (Chromium anti-detecção)
    browser/actions.py          → helpers: safe_click, safe_fill, close_modal etc.
    external_apis/triata_client.py  → TriataClient (login + extração de formulário)
    external_apis/zapsign_client.py → ZapSignClient (login + upload + assinatura)
    pdf/generator.py            → geração de PDF com reportlab
    storage/json_repository.py  → load/save/update dados em JSON
    storage/excel_repository.py → append em planilha Excel
```

## Detalhes operacionais

- **Browser**: `HEADLESS=false` por padrão, `SLOW_MO=50ms`, viewport 1920x1080, locale pt-BR. Anti-detecção: `navigator.webdriver = undefined`.
- **Triata**: login com credenciais fixas em `settings.py` (robo.cadastro). Busca a primeira tarefa de confecção disponível.
- **ZapSign**: credenciais via `.env` (`ZAPSIGN_EMAIL`, `ZAPSIGN_PASSWORD`). Login em 2 etapas (email → senha).
- **Timeouts**: default 30s, upload 3min, PDF viewer 90s, login 40s.
- **PDF**: dois templates conforme tarefa: "04.1" → carta proposta, "08" → contrato (template `modelo_contrato.txt`).

## Dados

- `dados_formulario_atual.json` — último candidato extraído (sobrescrito a cada execução)
- `dados_formularios.xlsx` — histórico (append)
- `pdfs_gerados/` — PDFs gerados
- Busca de PDF por nome normalizado (fallback para mais recente)

## .env

```env
ZAPSIGN_EMAIL=...@...
ZAPSIGN_PASSWORD=...
```

(ignorado pelo git; obrigatório para pipeline de assinatura)

## CI / Qualidade

CI em `.github/workflows/ci.yml` (GitHub Actions, Ubuntu, Python 3.12):

```bash
uv lock --check                    # verificar lock file
uv sync --all-extras --dev       # instalar deps + dev
uv run ruff check .              # lint
uv run ruff format --check .     # checar formatação
uv run mypy automation/            # type check
uv run python -c "import automation; print('Import OK')"  # importação
```

**Ruff** (`pyproject.toml`): line-length 100, double quotes, space indent, regras E/F/I/W/UP.  
**Mypy**: `strict = false`, ignora imports faltantes de `reportlab.*`, `playwright.*`, `pandas.*`, `openpyxl.*`, `pydantic_settings.*`.

Instalar dev tools localmente:

```bash
uv sync --all-extras --dev
```
