# set-fx-candidatos

Automação de proposta e assinatura digital para candidatos via Playwright (sync API). Código-fonte em português.

## Comandos

```bash
uv run python -m automation proposta      # fila Triata → N JSONs/Excel/PDFs (pula já processados)
uv run python -m automation assinatura    # envia PDF do "último" → ZapSign → link
uv run python -m automation finalizar     # cola signer_link no Triata + Prosseguir (espera modo teste manual)
uv run python -m automation completo      # proposta + assinatura + finalizar (1 candidato por vez)
```

Sem argumento = `proposta`. Entrypoint: `automation/__main__.py`. Argumento inválido imprime a lista acima.

## Pré-requisitos

- Python 3.12+ e `uv`
- `uv run playwright install chromium` (download do browser dedicado)
- `.env` na raiz com `ZAPSIGN_EMAIL` e `ZAPSIGN_PASSWORD` (obrigatórios para `assinatura`/`completo`). Ver `.env.example`. Triata usa credenciais fixas em `settings.py` (`robo.cadastro` / `Robo@aut2024`).

## Comportamento dos subcomandos

| Subcomando   | Retorno                             | Lê de                         | Escreve em                                                                                                           |
| ------------ | ----------------------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `proposta`   | `list[str]` (paths de PDFs gerados) | Triata                        | `dados/{processo_id}_{slug}.json`, `dados_formulario_atual.json` (último), `dados_formularios.xlsx`, `pdfs_gerados/` |
| `assinatura` | `str` (signer_link) ou `None`       | `dados_formulario_atual.json` | mesmo arquivo (chave `zapsign.link_assinatura`)                                                                      |
| `finalizar`  | `bool`                              | `dados_formulario_atual.json` | nada (preenche o Triata)                                                                                             |
| `completo`   | —                                   | encadeia os 3 acima           | —                                                                                                                    |

`proposta` processa **todos os candidatos de confecção** da fila do Triata numa única execução. Candidatos já processados (com JSON em `dados/{id}_*.json`) são pulados automaticamente. Lista vazia ou tudo já processado gera `logger.warning` (não é erro).

`completo` opera em **1 candidato por vez**: gera fila (pode ser N), mas `assinatura` e `finalizar` leem só o "último" do `dados_formulario_atual.json`. Para processar N candidatos completos, é necessário rodar `finalizar` N vezes (1 por candidato).

## Estrutura

### Entrypoints

- `automation/__main__.py` — CLI dispatcher (4 subcomandos)
- `automation/src/application/workflows/__init__.py` — exporta os 3 módulos de workflow
- `automation/src/application/workflows/gerar_proposta.py` — Pipeline 1 (fila Triata → PDFs)
- `automation/src/application/workflows/enviar_assinatura.py` — Pipeline 2 (ZapSign)
- `automation/src/application/workflows/finalizar_proposta.py` — Pipeline 3 (cola link no Triata)

### Clientes externos

- `automation/src/infrastructure/external_apis/triata_client.py` — `TriataClient`: `login`, `ativar_modo_teste`, `find_all_tasks` (N tarefas), `find_task` (1 tarefa, legado), `extract_form`, `run`
- `automation/src/infrastructure/external_apis/triata_finalizar_client.py` — `TriataFinalizarClient`: finaliza tarefa 04.1 no Triata após ZapSign
- `automation/src/infrastructure/external_apis/zapsign_client.py` — `ZapSignClient`: login 2-etapas → upload → config → vistos → assinatura → link

### Outras peças

- `automation/src/infrastructure/browser/factory.py` — `create_page()` (Chromium, anti-detecção)
- `automation/src/infrastructure/browser/actions.py` — `safe_click`/`safe_fill`/`close_modal`/`screenshot`/`click_canvas_center`/`scroll_viewer_to_bottom`/`wait_for_spinners`
- `automation/src/infrastructure/pdf/generator.py` — `generate_proposal_pdf` (reportlab) e `generate_contract_html` (HTML+Playwright)
- `automation/src/infrastructure/storage/json_repository.py` — JSON load/save + 5 funções `candidate_*` (fila)
- `automation/src/infrastructure/storage/excel_repository.py` — append via pandas/openpyxl
- `automation/src/application/services/branding_service.py` — temas, logos, assinaturas por empresa
- `automation/src/domain/models.py` — `Enterprise` enum (valores: `folhaTech`/`genter`/`arantes`), `Candidate`, `Proposal`, `Address`, `Signature`
- `automation/src/domain/exceptions.py` — hierarquia de exceções
- `automation/src/config/settings.py` — `Settings` via pydantic-settings, carrega `.env`

## Detalhes operacionais

- **Browser**: `HEADLESS=false`, `SLOW_MO=500ms`, viewport 1920x1080, locale pt-BR. Anti-detecção: `navigator.webdriver = undefined`, `--disable-blink-features=AutomationControlled`, user-agent Chrome 124.
- **Triata — login fixo** `robo.cadastro` / `Robo@aut2024` (em `settings.py`).
- **Triata — modo teste**: `TriataClient.ativar_modo_teste()` clica `.btn_ativa_modo_teste` e aceita diálogo. **Exceção:** `TriataFinalizarClient` **NÃO** ativa modo teste — espera até 120s pelo usuário ativar manualmente (`aguardar_modo_teste_manual`, detecta via `style.display === 'none'` no `span.btn_ativa_modo_teste`).
- **Triata — tarefas suportadas**: `04.1` (carta proposta), `05.1` (carta proposta, mesmo tratamento), `08` (contrato). `find_all_tasks` filtra por esses prefixos no `title` do `<td id="tarefa_NNN_M">`. Outras tarefas são ignoradas.
- **Triata — pós-save**: comportamento do Triata após salvar o formulário não foi confirmado. `gerar_proposta._voltar_para_lista()` usa heurística Y: espera 5s pelo seletor `td[id^="tarefa_"]` reaparecer; se não aparecer, faz `page.go_back()` e espera mais 10s.
- **Triata — finalização**: `TriataFinalizarClient.preencher_consideracoes` preenche `#ass_prestador` (link) e `#consideracoes_historico` (texto `"concluido pelo robo"`) via JS, disparando `input`/`change` e setando `bTeveAlteracao = true` quando existir. Botão Prosseguir usa seletor `button[onclick*="TriareSubmeteProcesso('G', 'N', '0121000001301'"]` (ID `0121000001301` é hardcoded — fixo até segunda ordem). Botão "Sim" confirma.
- **ZapSign — login 2 etapas**: email → "Entrar" → senha → "Entrar". Confirmação: `#button-create-doc-sidebar-test`.
- **ZapSign — pipeline**: upload → autenticação avançada (`#toggle-authentication-test-id-input`) → signatário → enviar (`#send-document-button-test`) → vistos em todas páginas (`#zs-options-lines-visto`) → campo de assinatura na última página (`#zs-options-lines-signature`) → Salvar e continuar → captura `input.signer_link`.
- **PDF tarefa "04.1"/"05.1"**: `generate_proposal_pdf` (reportlab) → `pdfs_gerados/Carta_Proposta_{Nome}_{processo_id}.pdf`. Saudação + tabelas de proposta/candidato/endereço + honorário + assinaturas + rodapé.
- **PDF tarefa "08"**: `generate_contract_html` (HTML+Playwright `page.pdf()`) → `pdfs_gerados/Contrato_{Nome}_{processo_id}.pdf`. Substitui `{{placeholders}}` em `modelo_contrato.html`, insere logo e assinaturas via base64. Template tem rodapé fixo e CSS A4.
- **Timeouts**: `DEFAULT_TIMEOUT=30s`, `UPLOAD_TIMEOUT=3min`, `PDF_VIEWER_TIMEOUT=90s`, `LOGIN_TIMEOUT=40s` (em `settings.py`).
- **Signature config**: `signatures.json` na raiz mapeia signatários por empresa/papel. Arquivos `.svg` em `signatures/`.
- **Logos**: `logos/<empresa>/` (ex: `logos/arantes/logo-v2.png`). `branding_service.find_logo` resolve por nome predefinido.

## Dados e persistência

| Local                                       | Conteúdo                              | Comportamento                                                                                                                                                                |
| ------------------------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dados/{processo_id}_{slug}.json`           | 1 candidato (dict achatado do Triata) | Criado/atualizado por `proposta` (via `save_candidate`). Filename: `{slug}` = `nome_completo` normalizado (sem acento, snake_case). `candidate_exists(id)` checa existência. |
| `dados_formulario_atual.json`               | Último candidato processado           | Sobrescrito a cada candidato da fila. Lido por `assinatura` e `finalizar`.                                                                                                   |
| `dados_formularios.xlsx` (planilha "Dados") | Histórico completo                    | Append (1 linha por candidato). Achata dicts aninhados com underscore.                                                                                                       |
| `pdfs_gerados/`                             | PDFs gerados                          | Acumula. `Carta_Proposta_{Nome}_{id}.pdf` ou `Contrato_{Nome}_{id}.pdf`.                                                                                                     |

**Importante**: o `dados_formulario_atual.json` é **regenerado** a cada iteração da fila (sempre o último). Se você processou 3 candidatos, o "atual" é o 3º, e rodar `assinatura` envia só esse 3º para ZapSign.

## CI (`.github/workflows/ci.yml`)

Ubuntu + Python 3.12:

```bash
uv lock --check
uv sync --all-extras --dev
uv run python -c "import automation; print('Import OK')"
```

Lint/typecheck locais (não no CI):

```bash
uv run ruff check .              # line-length 100, double quotes, space indent, regras E/F/I/W/UP, ignora E501
uv run ruff format --check .
uv run mypy automation/          # strict=false, ignora reportlab.*/playwright.*/pandas.*/openpyxl.*/pydantic_settings.*
uv sync --all-extras --dev       # instalar dev deps
```

## Onde mexer para...

| Quero...                                | Arquivo                                                                                             |
| --------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Adicionar novo campo extraído do Triata | (nada — extração é dinâmica via `extract_form`)                                                     |
| Mudar paleta/logo de uma empresa        | `automation/src/application/services/branding_service.py` + `logos/<empresa>/`                      |
| Adicionar novo template de PDF          | `automation/src/infrastructure/pdf/generator.py` + criar template na raiz                           |
| Mudar credenciais Triata                | `automation/src/config/settings.py` (ou `.env` com `TRIATA_USERNAME`/`TRIATA_PASSWORD`)             |
| Mudar fluxo de finalização no Triata    | `automation/src/infrastructure/external_apis/triata_finalizar_client.py`                            |
| Adicionar novo workflow/etapa           | Criar em `application/workflows/`, exportar em `__init__.py`, adicionar subcomando em `__main__.py` |
| Adicionar nova exceção tipada           | `automation/src/domain/exceptions.py` (subclasse de `AutomationError`)                              |
