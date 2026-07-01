# set-fx-candidatos

Automação de proposta e assinatura digital para candidatos via Playwright (sync API). Código-fonte em português.

## Comandos

```bash
uv run python -m automation proposta      # fila Triata → N JSONs/Excel/PDFs (pula já processados)
uv run python -m automation assinatura    # envia PDF do "último" → ZapSign → link
uv run python -m automation finalizar     # cola signer_link no Triata + Prosseguir + Sim
uv run python -m automation completo      # proposta + assinatura + finalizar (1 candidato por vez)
```

Sem argumento = `proposta`. Entrypoint: `automation/__main__.py`. Argumento inválido cai no `else` e imprime `Uso: python -m automation [proposta|assinatura|finalizar|completo]`.

## Pré-requisitos

- Python 3.12+ e `uv`
- `uv run playwright install chromium` (Chromium dedicado, **não** usa o do sistema)
- `.env` na raiz com `ZAPSIGN_EMAIL` e `ZAPSIGN_PASSWORD` (obrigatórios para `assinatura`/`completo`/`finalizar`). Ver `.env.example`. Triata usa credenciais fixas em `settings.py` (`robo.cadastro` / `Robo@aut2024`).

## Comportamento dos subcomandos

| Subcomando   | Retorno                             | Lê de                         | Escreve em                                                                                                           |
| ------------ | ----------------------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `proposta`   | `list[str]` (paths de PDFs gerados) | Triata                        | `dados/{processo_id}_{slug}.json`, `dados_formulario_atual.json` (último), `dados_formularios.xlsx`, `pdfs_gerados/` |
| `assinatura` | `str` (signer_link) ou `None`       | `dados_formulario_atual.json` | mesmo arquivo (chave `zapsign.link_assinatura`)                                                                      |
| `finalizar`  | `bool`                              | `dados_formulario_atual.json` | nada (preenche o Triata)                                                                                             |
| `completo`   | —                                   | encadeia os 3 acima           | —                                                                                                                    |

`proposta` processa **todos os candidatos de confecção** da fila do Triata numa única execução. Candidatos já processados (com JSON em `dados/{processo_id}_*.json`) são pulados via `candidate_exists(id)`. Lista vazia ou tudo já processado gera `logger.warning` (não é erro).

`completo` opera em **1 candidato por vez**: gera fila (pode ser N), mas `assinatura` e `finalizar` leem só o "último" do `dados_formulario_atual.json`. Para processar N candidatos completos, é necessário rodar `finalizar` N vezes (1 por candidato).

## Estrutura

### Entrypoints

- `automation/__main__.py` — CLI dispatcher (4 subcomandos)
- `automation/src/application/workflows/__init__.py` — exporta `gerar_proposta`, `enviar_assinatura`, `finalizar_proposta`
- `automation/src/application/workflows/gerar_proposta.py` — Pipeline 1 (fila Triata → PDFs)
- `automation/src/application/workflows/enviar_assinatura.py` — Pipeline 2 (ZapSign)
- `automation/src/application/workflows/finalizar_proposta.py` — Pipeline 3 (cola link no Triata)

### Clientes externos

- `automation/src/infrastructure/external_apis/triata_client.py` — `TriataClient`: `login`, `ativar_modo_teste`, `find_all_tasks` (N tarefas), `find_task` (1 tarefa, legado), `extract_form`, `run`
- `automation/src/infrastructure/external_apis/triata_finalizar_client.py` — `TriataFinalizarClient`: login → modo teste → clica tarefa 04.1/05.1/08 → preenche `#ass_prestador` (link) + `#consideracoes_historico` (texto) → Prosseguir → Sim
- `automation/src/infrastructure/external_apis/zapsign_client.py` — `ZapSignClient`: login 2-etapas → upload → config → vistos → assinatura → link

### Outras peças

- `automation/src/infrastructure/browser/factory.py` — `create_page()` (Chromium, anti-detecção)
- `automation/src/infrastructure/browser/actions.py` — `safe_click`/`safe_fill`/`close_modal`/`screenshot`/`click_canvas_center`/`scroll_viewer_to_bottom`/`wait_for_spinners`/`wait_for_value`
- `automation/src/infrastructure/pdf/generator.py` — `generate_proposal_pdf` (reportlab) e `generate_contract_html` (HTML+Playwright `page.pdf()`)
- `automation/src/infrastructure/storage/json_repository.py` — `load`/`save`/`update`/`save_signature_link`/`get_field` + 5 funções `candidate_*` (fila)
- `automation/src/infrastructure/storage/excel_repository.py` — `append` via pandas/openpyxl (achata dicts aninhados)
- `automation/src/application/services/branding_service.py` — temas, logos, contatos (`empresas.json`) e assinaturas (`signatures.json`)
- `automation/src/application/services/proposta_service.py` — `build_proposal(dict) → Proposal`
- `automation/src/domain/models.py` — `Enterprise` enum com valores `folhaTech`/`genter`/`arantes` (nota: o código de `find_signature_by_role` usa `empresa.value` para casar com `signatures.json`, que usa `folha_tech` snake_case — bug latente para Folha Tech), `Candidate`, `Proposal`, `Address`, `Signature`
- `automation/src/domain/exceptions.py` — `AutomationError` e subclasses
- `automation/src/domain/validators.py` — `normalize_text`, `clean_filename`, `clean_value`, `format_currency`, `is_checked`
- `automation/src/config/settings.py` — `Settings` via pydantic-settings, carrega `.env`

## Detalhes operacionais

- **Browser**: `HEADLESS=false`, `SLOW_MO=500ms`, viewport 1920x1080, locale pt-BR. Anti-detecção: `navigator.webdriver = undefined`, `--disable-blink-features=AutomationControlled`, user-agent Chrome 124.
- **Triata — login fixo** `robo.cadastro` / `Robo@aut2024` (em `settings.py`).
- **Triata — modo teste**: tanto `TriataClient.ativar_modo_teste()` quanto `TriataFinalizarClient.ativar_modo_teste()` (código duplicado) clicam `.btn_ativa_modo_teste` e aceitam diálogo; ambos têm fallback JS `ModoTeste('I')` se o botão não aparecer. Os dois fluxos ativam modo teste automaticamente — **não há etapa manual**.
- **Triata — tarefas suportadas**: `04.1` (carta proposta), `05.1` (carta proposta, mesmo tratamento), `08` (contrato). `find_all_tasks` filtra por substring `"04.1"`, `"05.1"` ou `"08"` no atributo `title` de `<td id="tarefa_NNN_M">`. Outras tarefas são ignoradas.
- **Triata — pós-save** (`gerar_proposta._voltar_para_lista`): espera 5s pelo seletor `td[id^="tarefa_"]` reaparecer; se não aparecer, faz `page.go_back()` e espera mais 10s.
- **Triata — finalização**: `preencher_consideracoes` preenche `#ass_prestador` (link ZapSign) e `#consideracoes_historico` (literal `"concluido pelo robo"`) via JS, disparando `input`/`change` e setando `bTeveAlteracao = true` quando existir. Botão Prosseguir usa seletor `button[onclick*="TriareSubmeteProcesso('G', 'N', '0121000001301'"]` (ID de modelo/área hardcoded). Botão "Sim" (`button:has-text("Sim")`) confirma. Falhas geram screenshots `erro_confirmacao_sim.png` e `erro_geral_finalizar_workflow.png` na raiz.
- **ZapSign — login 2 etapas**: email → "Entrar" → senha → "Entrar". Confirmação: `#button-create-doc-sidebar-test`.
- **ZapSign — pipeline**: upload (`#button-create-doc-sidebar-test` → `input#files`) → autenticação avançada (`#toggle-authentication-test-id-input`) → signatário (`#signer-name-field-test-id`) → enviar (`#send-document-button-test`) → vistos em todas páginas (`#zs-options-lines-visto` sobre `app-pdf-viewer .page[data-page-number] canvas`) → campo de assinatura na última página (`#zs-options-lines-signature` em `.pdfViewer .page[data-page-number]`) → Salvar e continuar (`#save-and-continue-btn-test`) → captura `input.signer_link` (aguarda `value.startsWith('http')` por 120s).
- **PDF tarefa "04.1"/"05.1"**: `generate_proposal_pdf` (reportlab) → `pdfs_gerados/Carta_Proposta_{Nome}_{processo_id}.pdf`. Saudação + tabelas de proposta/candidato/endereço + honorário + assinaturas + rodapé.
- **PDF tarefa "08"**: `generate_contract_html` (HTML+Playwright `page.pdf()`) → `pdfs_gerados/Contrato_{Nome}_{processo_id}.pdf`. Substitui `{{placeholders}}` em `modelo_contrato.html` (ou `modelo_contrato_30.html` se renomeado), insere logo e assinaturas via base64. Template tem rodapé fixo e CSS A4. Tem fallback visual "AAA / ARANTES ARIMURA" se nenhum logo for encontrado.
- **Timeouts**: `DEFAULT_TIMEOUT=30s`, `UPLOAD_TIMEOUT=3min`, `PDF_VIEWER_TIMEOUT=90s`, `LOGIN_TIMEOUT=40s` (em `settings.py`).
- **Signatures config**: `signatures.json` na raiz mapeia signatários por empresa/papel (`contratante`/`responsavel`/`testemunha`). Arquivos são `.png` (não `.svg`) em `signatures/` (`AssRapha.png`, `AssArimura.png`, `AssKarla.png`, `AssLuana.png`, `AssFernando.png`).
- **Logos**: `logos/<empresa>/` — pastas existentes: `logos/arantes/`, `logos/genter/`, `logos/folhaTech/` (camelCase para Folha Tech). `branding_service.find_logo` resolve por nome predefinido (`logo-v3.png` para Genter, `logo.png` para os outros) com fallback para primeiro `.png/.jpg/.jpeg/.webp` da pasta.
- **Template HTML**: `modelo_contrato.html` é o template ativo. Existe também `modelo_contrato_30.html` (variante). A config `TEMPLATE_CONTRATO=modelo_contrato.txt` em `settings.py` é legado e **não é usada** pelos workflows atuais — o que vale é `TEMPLATE_CONTRATO_HTML`.

## Dados e persistência

| Local                                       | Conteúdo                              | Comportamento                                                                                                                                                                |
| ------------------------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dados/{processo_id}_{slug}.json`           | 1 candidato (dict achatado do Triata) | Criado/atualizado por `proposta` (via `save_candidate`). `{slug}` = `nome_completo` normalizado (sem acento, snake_case). `candidate_exists(id)` checa existência.        |
| `dados_formulario_atual.json`               | Último candidato processado           | Sobrescrito a cada candidato da fila. Lido por `assinatura` e `finalizar`.                                                                                                   |
| `dados_formularios.xlsx` (planilha "Dados") | Histórico completo                    | Append (1 linha por candidato). Achata dicts aninhados com underscore. Reconstrói o arquivo inteiro a cada append (cuidado: não é append binário).                          |
| `pdfs_gerados/`                             | PDFs gerados                          | Acumula. `Carta_Proposta_{Nome}_{id}.pdf` ou `Contrato_{Nome}_{id}.pdf`. Criado automaticamente se não existir.                                                                |

**Importante**: o `dados_formulario_atual.json` é **regenerado** a cada iteração da fila (sempre o último). Se você processou 3 candidatos, o "atual" é o 3º. Rodar `assinatura` envia só esse 3º para ZapSign, e `finalizar` cola o link dele no Triata. Os 2 primeiros ficam com PDF + JSON em `dados/`, mas sem link de assinatura.

## CI (`.github/workflows/ci.yml`)

Ubuntu + Python 3.12:

```bash
uv lock --check
uv sync --all-extras --dev
uv run python -c "import automation; print('Import OK')"
```

**Atenção**: o CI **não roda pytest**. A pasta `tests/` contém scripts ad-hoc (`gerar_pdfs_teste.py`, `gerar_pdfs_teste_30.py`, `test_logo_contrato.py`, `test_logo_footer_contrato.py`) — alguns importam `automation` e podem ser executados manualmente, mas não há `conftest.py`, `pytest.ini` nem collection automática.

Lint/typecheck locais (não no CI):

```bash
uv run ruff check .              # line-length 100, double quotes, space indent, regras E/F/I/W/UP, ignora E501
uv run ruff format --check .
uv run mypy automation/          # strict=false, ignora reportlab.*/playwright.*/pandas.*/openpyxl.*/pydantic_settings.*
uv sync --all-extras --dev       # instalar dev deps (inclui pytest, mypy, ruff, pandas-stubs)
```

## Onde mexer para...

| Quero...                                | Arquivo                                                                                             |
| --------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Adicionar novo campo extraído do Triata | (nada — extração é dinâmica via `TriataClient.extract_form`)                                         |
| Mudar paleta/logo de uma empresa        | `automation/src/application/services/branding_service.py` + `logos/<empresa>/` + `empresas.json`     |
| Adicionar novo template de PDF          | `automation/src/infrastructure/pdf/generator.py` + criar template na raiz (`modelo_contrato.html`)  |
| Mudar credenciais Triata                | `automation/src/config/settings.py` (ou `.env` com `TRIATA_USERNAME`/`TRIATA_PASSWORD`)             |
| Mudar fluxo de finalização no Triata    | `automation/src/infrastructure/external_apis/triata_finalizar_client.py`                            |
| Adicionar novo workflow/etapa           | Criar em `application/workflows/`, exportar em `__init__.py`, adicionar subcomando em `__main__.py` |
| Adicionar nova exceção tipada           | `automation/src/domain/exceptions.py` (subclasse de `AutomationError`) e re-exportar em `__init__.py` |
