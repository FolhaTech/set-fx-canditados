# set-fx-candidatos

**Automação de proposta e assinatura digital para candidatos.**

---

## Índice

1. [Visão Geral](#visão-geral)
2. [Contexto e Motivação](#contexto-e-motivação)
3. [Stack](#stack)
4. [Pré-requisitos](#pré-requisitos)
5. [Instalação](#instalação)
6. [Configuração](#configuração)
7. [Uso](#uso)
8. [Arquitetura](#arquitetura)
9. [Fluxo de Dados](#fluxo-de-dados)
10. [Pipelines em Detalhe](#pipelines-em-detalhe)
11. [Temas e Branding](#temas-e-branding)
12. [Dicionário de Dados](#dicionário-de-dados)
13. [Modelos de Domínio](#modelos-de-domínio)
14. [Validadores](#validadores)
15. [Tratamento de Erros](#tratamento-de-erros)
16. [Estratégias de Resiliência no Browser](#estratégias-de-resiliência-no-browser)
17. [Anti-Detecção do Browser](#anti-detecção-do-browser)
18. [Logging](#logging)
19. [Persistência](#persistência)
20. [Troubleshooting](#troubleshooting)
21. [Exemplos de Saída](#exemplos-de-saída)
22. [Considerações de Segurança](#considerações-de-segurança)
23. [Desenvolvimento](#desenvolvimento)
24. [Manutenção](#manutenção)
25. [Limitações Conhecidas](#limitações-conhecidas)
26. [Licença](#licença)

---

## Visão Geral

Este projeto automatiza o fluxo completo de contratação de candidatos em duas pipelines independentes mas complementares:

1. **Pipeline de Proposta** — Acessa o sistema **Triata** (plataforma de workflow interna da Folha Tech), extrai os dados do formulário do candidato, gera um documento PDF (carta proposta ou contrato, conforme o tipo de tarefa) e persiste os dados em JSON e Excel para rastreabilidade.

2. **Pipeline de Assinatura** — Envia o PDF gerado para a plataforma **ZapSign** (serviço de assinatura digital), configura o documento (autenticação avançada, signatário, vistos em todas as páginas, campo de assinatura) e captura o link público para o candidato assinar eletronicamente.

Ambas as pipelines são executadas via **Playwright** (API síncrona) em navegador Chromium, com múltiplas estratégias de resiliência para lidar com modais, timeouts e elementos dinâmicos.

---

## Contexto e Motivação

A contratação de candidatos na Folha Tech e empresas do grupo (Genter, Arantes) envolve um processo multi-etapas no sistema Triata:

- **Tarefa 04.1 — Confecção de Proposta**: Gerar uma carta de proposta com dados do candidato, honorários, equipamentos e sistemas.
- **Tarefa 08 — Confecção e Assinatura de Contrato**: Gerar um contrato formal e enviar para assinatura digital via ZapSign.

Cada execução manual dessas tarefas consumia tempo de operadores de TI, envolvendo: login no Triata, navegação até a tarefa, extração manual dos dados do formulário, preenchimento de templates, formatação de PDF, login no ZapSign, upload de documento, configuração de signatários, aplicação de vistos e assinaturas, e cópia manual do link.

Este projeto elimina 100% das etapas manuais, reduzindo o tempo de processamento de ~15 minutos para ~3 minutos por candidato, com zero erro de transcrição de dados.

---

## Stack

| Tecnologia                       | Versão / Requisito | Função                                                                 |
| -------------------------------- | ------------------ | ---------------------------------------------------------------------- |
| Python                           | `>= 3.12`          | Linguagem de programação                                               |
| [uv](https://docs.astral.sh/uv/) | latest             | Gerenciador de pacotes e lockfile (`uv.lock`)                          |
| Playwright                       | `>= 1.60.0`        | Automação de navegador (API síncrona)                                  |
| pydantic-settings                | `>= 2.14.1`        | Configuração via `.env` e variáveis de ambiente com validação de tipos |
| reportlab                        | `>= 4.5.1`         | Geração programática de PDF                                            |
| pandas                           | `>= 2.0`           | Manipulação de dados tabulares                                         |
| openpyxl                         | via pandas         | Leitura/escrita de planilhas Excel (.xlsx)                             |
| pandas-stubs                     | `~= 3.0.3`         | Stubs de tipos para pandas (desenvolvimento)                           |

---

## Pré-requisitos

### 1. Python

O projeto requer **Python 3.12 ou superior**. Para verificar:

```bash
python --version
# ou
python3 --version
```

### 2. Gerenciador de Pacotes `uv`

O projeto usa `uv` como gerenciador de pacotes. Instalação:

```bash
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Navegadores Chromium para Playwright

Após instalar dependências, instale os navegadores:

```bash
uv run playwright install chromium
```

Isso baixa o Chromium dedicado para Playwright (não usa o Chromium do sistema).

### 4. Arquivo `.env`

Crie um arquivo `.env` na **raiz do projeto** com as credenciais do ZapSign:

```env
ZAPSIGN_EMAIL=seu@email.com
ZAPSIGN_PASSWORD=sua_senha
```

> **Nota**: O arquivo `.env` está listado no `.gitignore` e nunca deve ser commitado.

---

## Instalação

```bash
# Clone ou navegue até o diretório do projeto
cd set-fx-candidatos

# Instala todas as dependências travadas em uv.lock
uv sync
```

O comando `uv sync` instala exatamente as versões travadas no lockfile, garantindo reprodutibilidade.

Para atualizar para versões mais recentes:

```bash
uv sync --upgrade
```

---

## Configuração

Todas as configurações estão centralizadas em `automation/src/config/settings.py` e são carregadas via **pydantic-settings** (`BaseSettings` com `SettingsConfigDict`). A configuração é carregada na ordem:

1. Variáveis de ambiente (maior prioridade)
2. Arquivo `.env` na raiz do projeto
3. Valores padrão definidos no código (menor prioridade)

### Variáveis de Ambiente / `.env`

| Variável           | Padrão                                                                        | Descrição                      | Obrigatório               |
| ------------------ | ----------------------------------------------------------------------------- | ------------------------------ | ------------------------- |
| `TRIATA_URL`       | `https://workflow.folhatech.com.br/triata/Sistema.php?area=Processo&m=1&mp=1` | URL do sistema Triata          | Não                       |
| `TRIATA_USERNAME`  | `robo.cadastro`                                                               | Usuário de serviço para Triata | Não                       |
| `TRIATA_PASSWORD`  | `Robo@aut2024`                                                                | Senha do usuário Triata        | Não                       |
| `ZAPSIGN_URL`      | `https://app.zapsign.com.br/acesso/entrar`                                    | URL de login do ZapSign        | Não                       |
| `ZAPSIGN_EMAIL`    | `""`                                                                          | Email da conta ZapSign         | **Sim** (para assinatura) |
| `ZAPSIGN_PASSWORD` | `""`                                                                          | Senha da conta ZapSign         | **Sim** (para assinatura) |

### Timeouts (em milissegundos)

| Config               | Padrão  | Contexto                        | Onde usado                                     |
| -------------------- | ------- | ------------------------------- | ---------------------------------------------- |
| `DEFAULT_TIMEOUT`    | 30.000  | Operações gerais do Playwright  | `safe_click`, `safe_fill`, `wait_for_selector` |
| `UPLOAD_TIMEOUT`     | 180.000 | Upload de PDF no ZapSign        | `apply_verification_marks` (viewer carregar)   |
| `PDF_VIEWER_TIMEOUT` | 90.000  | Aguardar viewer do PDF carregar | `place_signature_field`                        |
| `LOGIN_TIMEOUT`      | 40.000  | Login no Triata                 | `TriataClient.login()`                         |

### Configurações do Browser

| Config            | Padrão                                                                                                            | Descrição                          | Impacto                                        |
| ----------------- | ----------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ---------------------------------------------- |
| `HEADLESS`        | `false`                                                                                                           | Executar navegador em modo visível | Útil para debug; em servidores, definir `true` |
| `SLOW_MO`         | `50`                                                                                                              | Atraso entre ações (ms)            | Aumenta se a rede estiver lenta                |
| `VIEWPORT_WIDTH`  | `1920`                                                                                                            | Largura da viewport                | Deve refletir resolução comum do usuário       |
| `VIEWPORT_HEIGHT` | `1080`                                                                                                            | Altura da viewport                 | Deve refletir resolução comum do usuário       |
| `BROWSER_LOCALE`  | `pt-BR`                                                                                                           | Locale do navegador                | Afeta formatação de datas, números             |
| `USER_AGENT`      | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36` | User-Agent customizado             | Anti-detecção: imita navegador real            |

### Caminhos de Arquivos

| Config              | Padrão                        | Tipo      | Descrição                                         |
| ------------------- | ----------------------------- | --------- | ------------------------------------------------- |
| `PDF_DIR`           | `pdfs_gerados`                | Diretório | Onde os PDFs são salvos                           |
| `LOGOS_DIR`         | `Logos`                       | Diretório | Logos por empresa (subdiretórios)                 |
| `ASSINATURAS_DIR`   | `assinatura`                  | Diretório | Imagens de assinatura digital                     |
| `TEMPLATE_CONTRATO` | `modelo_contrato.txt`         | Arquivo   | Template de contrato com placeholders `{{campo}}` |
| `JSON_FILE`         | `dados_formulario_atual.json` | Arquivo   | Último candidato extraído                         |
| `EXCEL_FILE`        | `dados_formularios.xlsx`      | Arquivo   | Histórico de candidatos (append)                  |

---

## Uso

O entrypoint do projeto é o módulo `automation`, executado via:

```bash
uv run python -m automation [etapa]
```

### Comandos Disponíveis

| Comando                                  | Descrição                                                           | Requisitos                                    |
| ---------------------------------------- | ------------------------------------------------------------------- | --------------------------------------------- |
| `uv run python -m automation`            | Executa a pipeline de **Proposta** (padrão)                         | Triata acessível                              |
| `uv run python -m automation proposta`   | Extrai dados do Triata, salva em JSON/Excel e gera PDF              | Triata acessível                              |
| `uv run python -m automation assinatura` | Lê o último JSON, localiza o PDF e envia para assinatura no ZapSign | `.env` com credenciais ZapSign; PDF existente |
| `uv run python -m automation completo`   | Executa `proposta` e `assinatura` em sequência                      | Todos os requisitos acima                     |

### Comportamento Padrão

Se nenhum argumento for passado, o CLI dispatcher (`automation/__main__.py`) executa `proposta` por padrão.

### Exemplo de Execução Completa

```bash
# 1. Gera proposta (acessa Triata, extrai, gera PDF)
uv run python -m automation proposta

# 2. Envia para assinatura (usa o PDF gerado)
uv run python -m automation assinatura

# Ou, em um único comando:
uv run python -m automation completo
```

### Output Esperado

Durante a execução, o console exibe logs em tempo real:

```
12:34:56  [INFO   ]  === PIPELINE 1: Gerar Proposta ===
12:34:57  [INFO   ]  Acessando Triata...
12:34:59  [INFO   ]  Preenchendo login...
12:35:00  [INFO   ]  Aguardando listagem de tarefas...
12:35:02  [INFO   ]  Encontradas 3 tarefas.
12:35:02  [INFO   ]  Tarefa: 04.1 - Confecção Proposta | Processo: 12345
12:35:03  [INFO   ]  Total de 45 campos extraídos.
12:35:03  [INFO   ]  Dados salvos em JSON e Excel.
12:35:04  [INFO   ]  PDF da carta proposta gerado: pdfs_gerados/Carta_Proposta_Joao_Silva.pdf
12:35:04  [INFO   ]  Navegador fechado.

12:35:05  [INFO   ]  === PIPELINE 2: Enviar para Assinatura ===
12:35:06  [INFO   ]  Candidato: João Silva | Email: joao@email.com
12:35:06  [INFO   ]  PDF para upload: pdfs_gerados/Carta_Proposta_Joao_Silva.pdf
12:35:07  [INFO   ]  Acessando ZapSign...
12:35:09  [INFO   ]  Login ZapSign confirmado.
12:35:10  [INFO   ]  Link capturado: https://app.zapsign.com.br/ver/abcd1234
```

---

## Arquitetura

O projeto segue uma arquitetura em camadas com separação de responsabilidades:

```
set-fx-candidatos/
├── .env                          # Credenciais ZapSign (ignorado pelo git)
├── pyproject.toml                # Metadados e dependências do projeto
├── uv.lock                       # Lockfile do uv (reprodutibilidade)
├── AGENTS.md                     # Instruções compactas para sessões OpenCode
├── dados_formulario_atual.json   # Último candidato extraído (sobrescrito a cada execução)
├── dados_formularios.xlsx        # Histórico de candidatos (append)
├── pdfs_gerados/                 # PDFs gerados (carta proposta ou contrato)
│
├── Logos/                        # [opcional] Imagens de logo por empresa
│   ├── Folha Tech/               #   → Qualquer .png/.jpg/.webp (primeiro encontrado)
│   ├── Genter/
│   └── Arantes/
│
├── assinatura/                   # [opcional] Imagens de assinatura digital
│   ├── AssArimura.png            #   → Genter
│   ├── AssRapha.png              #   → Arantes
│   └── AssFernando.png           #   → Folha Tech
│
├── modelo_contrato.txt           # [opcional] Template para tarefas tipo "08" (contrato)
│                                   #   → Placeholders: {{nome_do_campo}}
│
└── automation/                   # Pacote principal
    ├── __main__.py               # CLI dispatcher (entrypoint)
    │
    └── src/
        ├── config/
        │   ├── __init__.py       # Exporta: Settings, settings, setup_logging, get_logger
        │   ├── settings.py       # Settings via pydantic-settings (carrega .env da raiz)
        │   └── logging_config.py # Log formatado com supressão de libs ruidosas
        │
        ├── domain/               # Regras de negócio puras (sem dependências externas)
        │   ├── __init__.py       # Export público: models, exceptions, validators
        │   ├── models.py         # Candidate, Proposal, Enterprise (Enum), Address, Signature
        │   ├── validators.py     # normalize_text, clean_filename, format_currency, is_checked...
        │   └── exceptions.py     # Hierarquia de exceções
        │
        ├── application/          # Orquestração de casos de uso
        │   ├── workflows/
        │   │   ├── __init__.py              # Exporta: gerar_proposta, enviar_assinatura
        │   │   ├── gerar_proposta.py        # Pipeline 1: Triata → dados → PDF
        │   │   └── enviar_assinatura.py     # Pipeline 2: PDF → ZapSign → link
        │   └── services/
        │       ├── proposta_service.py      # build_proposal(dict) → Proposal
        │       └── branding_service.py      # Temas, logos e assinaturas por empresa
        │
        └── infrastructure/       # Implementações técnicas (browser, APIs, storage, PDF)
            ├── browser/
            │   ├── factory.py   # create_page() — Chromium anti-detecção
            │   └── actions.py   # safe_click, safe_fill, close_modal, click_canvas_center...
            ├── external_apis/
            │   ├── triata_client.py   # TriataClient: login → find_task → extract_form
            │   └── zapsign_client.py  # ZapSignClient: login → upload → config → sign → link
            ├── pdf/
            │   ├── generator.py  # generate_proposal_pdf(), generate_contract_pdf()
            │   └── styles.py     # Estilos tipográficos (build_styles)
            └── storage/
                ├── json_repository.py  # load, save, update, save_signature_link, get_field
                └── excel_repository.py # append (flatten dict → pandas → openpyxl)
```

### Camadas

1. **Domain** (`src/domain/`): Contém entidades (`Candidate`, `Proposal`, `Enterprise`), validadores e exceções. É a camada mais interna, sem dependências de infraestrutura.
2. **Application** (`src/application/`): Orquestra fluxos de trabalho (workflows) e converte dados brutos (dict) em modelos de domínio (services).
3. **Infrastructure** (`src/infrastructure/`): Implementa detalhes técnicos: automação de browser, comunicação com APIs externas, geração de PDF, persistência.
4. **Config** (`src/config/`): Centraliza configuração e logging.

---

## Fluxo de Dados

```
┌─────────────────┐
│  Triata (Web)   │
│  workflow.folha-│
│  tech.com.br    │
└────────┬────────┘
         │  [Playwright]
         │  login → clica 1ª tarefa
         │  → extrai #TriareProcessoForm via JS
         ▼
┌─────────────────────────────┐
│ dados_formulario_atual.json │  ◄── Sobrescrito a cada execução
│ (dict completo do formulário)│
└─────────────┬───────────────┘
              │
              ├──► ┌─────────────────────────┐
              │    │ dados_formularios.xlsx   │
              │    │ (append histórico)       │
              │    └─────────────────────────┘
              │
              └──► ┌─────────────────────────┐
                   │ build_proposal(dados)    │
                   │   → Proposal (dataclass)  │
                   └────────────┬────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
         Tarefa "04.1"              Tarefa "08"
              │                       │
              ▼                       ▼
    ┌─────────────────┐    ┌──────────────────────┐
    │ generate_proposal│    │ generate_contract_pdf│
    │ _pdf()           │    │ (template {{fields}})│
    └────────┬────────┘    └──────────┬─────────┘
             │                         │
             ▼                         ▼
    ┌─────────────────┐    ┌──────────────────────┐
    │Carta_Proposta_  │    │ Contrato_NOME.pdf    │
    │NOME.pdf          │    └──────────┬─────────┘
    │(em pdfs_gerados/)│               │
    └────────┬────────┘               │
             │                        │
             │         ┌──────────────┘
             │         │
             │         ▼
             │  ┌─────────────────┐
             │  │  ZapSign (Web)   │
             │  │ app.zapsign.com  │
             │  │ .br              │
             │  └────────┬────────┘
             │           │  [Playwright]
             │           │  upload → config → sign
             │           ▼
             │  ┌─────────────────────┐
             │  │ Link de assinatura  │
             │  │ (URL pública)       │
             │  └──────────┬──────────┘
             │             │
             │             ▼
             │  ┌─────────────────────────────┐
             └──►│ dados_formulario_atual.json │
                │  + zapsign.link_assinatura   │
                │  + zapsign.capturado_em       │
                └─────────────────────────────┘
```

---

## Pipelines em Detalhe

### Pipeline 1: Proposta (`automation/src/application/workflows/gerar_proposta.py`)

#### 1. Inicialização do Browser

A função `create_page()` (em `browser/factory.py`) inicia o Playwright com as seguintes configurações:

- **Browser**: Chromium via `sync_playwright().start()`
- **Args**: `--start-maximized`, `--disable-blink-features=AutomationControlled`
- **Anti-detecção**: Script de inicialização que define `navigator.webdriver = undefined`
- **Contexto**: `ignore_https_errors=true`, `locale=pt-BR`, user-agent customizado

#### 2. Login no Triata

O `TriataClient.login()` executa:

1. `page.goto(TRIATA_URL)` com `wait_until="domcontentloaded"` e timeout de 40s
2. Aguarda `networkidle` (timeout 30s)
3. Preenche `input[name="login"]` com `robo.cadastro`
4. Preenche `input[name="senha"]` com `Robo@aut2024`
5. Clica em `#TriataBtAcessar`
6. Aguarda o campo de login sumir (`state="hidden"`, timeout 30s)
7. Se o campo continuar visível, levanta `TriataLoginError`

#### 3. Busca de Tarefa

O `TriataClient.find_task()`:

1. Aguarda seletores `td[id^="tarefa_"]` (timeout 20s)
2. Pega a **primeira tarefa** da lista (assumindo que a ordem é cronológica ou prioritária)
3. Extrai o atributo `title` e `id` do `<td>`
4. Classifica o tipo:
   - Se `"04.1"` no título → `nome_tarefa = "04.1 - Confecção Proposta"`
   - Se `"08"` no título → `nome_tarefa = "08 - Confecção e assinatura (Contrato)"`
   - Senão → `TarefaNotFoundError`
5. Extrai `processo_id` do padrão regex `tarefa_(\d+)_\d+`
6. Aceita qualquer diálogo (`dialog.accept()`)
7. Clica na tarefa e aguarda o formulário `#TriareProcessoForm` (timeout 20s)

#### 4. Extração do Formulário

O `TriataClient.extract_form()` executa JavaScript no browser para extrair todos os campos do formulário `#TriareProcessoForm`:

```javascript
const form = document.querySelector("#TriareProcessoForm");
const elements = form.querySelectorAll("input, select, textarea");
elements.forEach((el) => {
  const key = el.id || el.name;
  if (el.type === "checkbox" || el.type === "radio") {
    data[key] = el.checked ? el.value || true : false;
  } else if (el.tagName === "SELECT") {
    data[key] = el.options[el.selectedIndex]?.text.trim() || "";
  } else {
    data[key] = el.value || "";
  }
});
```

O resultado é um dict com ~40-50 campos, incluindo metadados `extraido_em` e `url`.

#### 5. Persistência

- **JSON**: `save(settings.json_path, dados)` — sobrescreve o arquivo anterior
- **Excel**: `append_excel(settings.excel_path, dados)` — achata dicts aninhados e concatena com planilha existente

#### 6. Montagem do Modelo Proposal

A função `build_proposal(dados)` (em `proposta_service.py`) realiza:

- **Candidate**: Extrai nome, email, CPF, RG, data de nascimento, estado civil, celular, endereço
- **Address**: Logradouro, número, complemento, bairro, cidade, CEP
- **Empresa**: Resolve a partir dos campos `empresa_colaborador_novo` ou `empresa_solicitante` via `Enterprise.from_string()`
- **Honorário**: Parse de `honorario_novo_colaborador` (remove pontos, converte vírgula → ponto → float)
- **Equipamentos e Sistemas**: Extração de itens com checkbox `[x]` marcado dos grupos `equipamentos` e `sistemas`
- **Metadados**: `processo_id`, `tarefa_nome`, `modelo_nome`

#### 7. Geração de PDF

A decisão de qual PDF gerar é baseada em `tarefa_nome`:

**Se a tarefa contém "04.1":**

- Gera `Carta_Proposta_{nome_sanitizado}.pdf`
- PDF estilizado com:
  - Logo da empresa (se encontrado em `Logos/<Empresa>/`)
  - Data de São Paulo (formato `dd/MM/yyyy`)
  - Saudação ao candidato
  - Tabela "Dados da proposta" (processo, tarefa, modelo, empresa, tipo de vaga, centro de custo, honorário)
  - Tabela "Dados do candidato" (nome, nascimento, estado civil, RG, CPF, email, celular)
  - Tabela "Endereço residencial"
  - Listas de equipamentos e sistemas
  - Condições (honorário formatado como `R$ 1.234,56`)
  - Campos de assinatura (candidato + responsável legal)
  - Imagem de assinatura digital (se encontrada)
  - Rodapé com mensagem de automação

**Se a tarefa contém "08":**

- Gera `Contrato_{nome_sanitizado}.pdf`
- Lê o arquivo `modelo_contrato.txt`
- Substitui todos os placeholders `{{campo}}` pelos valores extraídos do JSON
- Campos com "honorario" ou "valor" no nome são formatados como moeda
- Renderiza como texto justificado com quebra de linhas

**Se a tarefa não contém nem "04.1" nem "08":**

- Gera log informativo e retorna `None`

#### 8. Encerramento

- Fecha o browser (`page.context.browser.close()`)
- Retorna o caminho absoluto do PDF gerado

---

### Pipeline 2: Assinatura (`automation/src/application/workflows/enviar_assinatura.py`)

#### 1. Validação de Pré-requisitos

- Verifica se `ZAPSIGN_EMAIL` e `ZAPSIGN_PASSWORD` estão definidos (senão, `MandatoryFieldError`)
- Lê `nome_completo` e `email_pessoal_candidato` do JSON atual
- `nome_completo` é obrigatório (`required=True`)

#### 2. Busca do PDF

A função `_find_pdf()`:

1. Lista todos os arquivos `.pdf` em `pdfs_gerados/`
2. Normaliza o nome do candidato via `normalize_text()` (remove acentos, minúsculas, espaços normalizados)
3. Busca PDFs cujo nome contenha o nome normalizado (ou vice-versa)
4. Se múltiplos matches, pega o mais recente (ordenado por `st_mtime`)
5. Se nenhum match, fallback para o PDF mais recente do diretório
6. Se diretório vazio, retorna `None` e loga erro

#### 3. Login no ZapSign

O `ZapSignClient.login()`:

1. Acessa a URL de login
2. `close_modal()` — fecha qualquer modal de boas-vindas
3. **Etapa 1**: Preenche email em `input[inputmode="email"]` ou com placeholder de e-mail
4. Clica no botão "Entrar" (`.first`)
5. **Etapa 2**: Aguarda `input[type="password"]` visível (timeout 20s)
6. Preenche senha
7. Clica no botão "Entrar" (`.last`)
8. Aguarda o botão `#button-create-doc-sidebar-test` (timeout 40s)

#### 4. Criação e Upload do Documento

O `ZapSignClient.create_and_upload()`:

1. Clica em `#button-create-doc-sidebar-test`
2. Aguarda o input de arquivo `input#files[type="file"]` (state="attached", timeout 30s)
3. Define os arquivos via `set_input_files(pdf_paths)`
4. Aguarda spinners/processamento (`wait_for_spinners()`)
5. Clica em `[data-cy="continuarBtn"]`
6. Aguarda `domcontentloaded` e fecha modais

#### 5. Autenticação Avançada

O `ZapSignClient.enable_advanced_auth()`:

1. Localiza o toggle `#toggle-authentication-test-id-input`
2. Se `aria-checked` não for `true`, clica no label correspondente
3. Aguarda via `page.wait_for_function()` até o atributo mudar para `true` (timeout 15s)

#### 6. Preenchimento do Signatário

O `ZapSignClient.fill_signer_info()`:

1. Preenche `signer-name-field-test-id` com o nome do candidato
2. Aguarda via `wait_for_value()` que o campo tenha valor (`value.trim().length > 0`)
3. Se email fornecido, preenche `signer-email-field-test-id`
4. Aguarda que o email contenha `@`

#### 7. Envio do Documento

O `ZapSignClient.send_document()`:

1. Clica em `#send-document-button-test`
2. Aguarda `domcontentloaded`
3. Fecha modais

#### 8. Aplicação de Vistos

O `ZapSignClient.apply_verification_marks()`:

1. Aguarda `app-pdf-viewer .page[data-page-number]` (timeout 180s)
2. Aguarda canvas dentro de cada página (timeout 180s)
3. Conta o total de páginas
4. Para cada página:
   - Fecha modais
   - Faz scroll até a página
   - Clica no centro do canvas (`click_canvas_center`)
   - Seleciona a opção "Visto" (`#zs-options-lines-visto`)
   - Loga o sucesso

#### 9. Inserção de Campo de Assinatura

O `ZapSignClient.place_signature_field()`:

1. Aguarda `.pdfViewer` (timeout 90s)
2. Aguarda páginas e canvas dentro do viewer
3. Para cada viewer:
   - Faz scroll até o final (`scroll_viewer_to_bottom`)
   - Conta as páginas
   - Tenta inserir assinatura na última página (e penúltima, se houver >= 2)
   - Clica no canvas e seleciona `#zs-options-lines-signature`

4. Se não encontrar `.pdfViewer`, usa fallback global (todas as páginas do documento)

#### 10. Salvar e Continuar

O `ZapSignClient.save_and_continue()`:

1. Clica em `#save-and-continue-btn-test`
2. Aguarda `domcontentloaded`

#### 11. Captura do Link

O `ZapSignClient.capture_link()`:

1. Aguarda via `page.wait_for_function()` até encontrar um `input.signer_link` com valor começando com `http` (timeout 120s)
2. Extrai o valor do input
3. Valida que começa com `http` (senão, `ZapSignLinkError`)
4. Loga o link capturado
5. Retorna o link

#### 12. Persistência do Link

O link é salvo no JSON via `save_signature_link()`:

```json
{
  "zapsign": {
    "link_assinatura": "https://app.zapsign.com.br/ver/abcd1234",
    "capturado_em": "2024-01-15 14:30:00"
  }
}
```

#### 13. Encerramento

- Fecha o browser
- Retorna o link

---

## Temas e Branding

Cada empresa do grupo tem identidade visual própria, configurada em `branding_service.py`:

### Paletas de Cores

| Empresa        | Primária             | Secundária                | Texto     |
| -------------- | -------------------- | ------------------------- | --------- |
| **Folha Tech** | `#F58220` (Laranja)  | `#FFE8D1` (Laranja claro) | `#333333` |
| **Genter**     | `#9E2F2A` (Vermelho) | `#F6E3E2` (Rosa claro)    | `#333333` |
| **Arantes**    | `#1D4ED8` (Azul)     | `#DBEAFE` (Azul claro)    | `#333333` |

### Resolução de Empresa

A função `Enterprise.from_string()` normaliza o texto e retorna:

- `"folha" + "tech"` → `Enterprise.FOLHA_TECH`
- `"arantes"` ou `"aaa"` → `Enterprise.ARANTES`
- `"genter"` ou qualquer outro → `Enterprise.GENTER` (padrão)

### Logos

- **Local**: `Logos/<Nome da Empresa>/`
- **Formatos suportados**: `.png`, `.jpg`, `.jpeg`, `.webp`
- **Comportamento**: Pega o primeiro arquivo encontrado (ordem do sistema de arquivos)
- **Fallback**: Se não houver logo, o nome da empresa é renderizado em texto grande e centralizado

### Assinaturas Digitais

| Empresa    | Arquivo Esperado             |
| ---------- | ---------------------------- |
| Genter     | `assinatura/AssArimura.png`  |
| Arantes    | `assinatura/AssRapha.png`    |
| Folha Tech | `assinatura/AssFernando.png` |

- **Fallback**: Se não houver imagem, a assinatura é renderizada como linha de texto
- **Dimensões no PDF**: 4.5cm × 1.8cm

---

## Dicionário de Dados

### Campos Extraídos do Triata (JSON)

Os campos a seguir são extraídos automaticamente do formulário `#TriareProcessoForm`:

#### Metadados do Processo

| Campo                     | Tipo | Descrição                            | Exemplo                                    |
| ------------------------- | ---- | ------------------------------------ | ------------------------------------------ |
| `extraido_em`             | str  | Timestamp da extração                | `"05/06/2026, 10:41:31"`                   |
| `url`                     | str  | URL da página no momento da extração | `"https://workflow.folhatech.com.br/..."`  |
| `processo_id`             | str  | ID do processo (extraído do DOM)     | `"22133"`                                  |
| `tarefa_nome`             | str  | Nome normalizado da tarefa           | `"08 - Confecção e assinatura (Contrato)"` |
| `modelo_nome`             | str  | Nome do modelo do processo           | `"Arantes - Contratação PJ"`               |
| `amb_tarefa_id`           | str  | ID interno da tarefa                 | `"127857"`                                 |
| `amb_usuario_nome`        | str  | Nome do usuário logado               | `"Robo Cadastro Cliente"`                  |
| `amb_data_hora_formatada` | str  | Data/hora da extração                | `"05/06/2026 10:33"`                       |

#### Dados do Solicitante

| Campo                 | Descrição                     |
| --------------------- | ----------------------------- |
| `nome_solicitante`    | Nome de quem abriu o processo |
| `email_solicitante`   | Email do solicitante          |
| `solicitante_empresa` | Empresa do solicitante        |

#### Dados do Candidato

| Campo                     | Descrição                  | Usado em        |
| ------------------------- | -------------------------- | --------------- |
| `nome_completo`           | Nome completo do candidato | PDF, assinatura |
| `data_nascimento`         | Data de nascimento         | PDF             |
| `estado_civil`            | Estado civil               | PDF             |
| `nome_pai`                | Nome do pai                | —               |
| `nome_mae`                | Nome da mãe                | —               |
| `nome_fantasia`           | Nome fantasia              | —               |
| `rg_candidato`            | Número do RG               | PDF             |
| `cpf_candidato`           | CPF (formatado)            | PDF             |
| `email_pessoal_candidato` | Email pessoal              | PDF, assinatura |
| `celular_candidato`       | Celular pessoal            | PDF             |
| `cnpj_candidato`          | CNPJ (se PJ)               | —               |

#### Endereço

| Campo                  | Descrição   |
| ---------------------- | ----------- |
| `endereco_completo`    | Logradouro  |
| `numero_endereco`      | Número      |
| `complemento_endereco` | Complemento |
| `cep_prestador`        | CEP         |
| `bairro_prestador`     | Bairro      |
| `cidade_prestador`     | Cidade      |

#### Dados da Proposta

| Campo                        | Descrição                                | Usado em                  |
| ---------------------------- | ---------------------------------------- | ------------------------- |
| `tipo_vaga`                  | Tipo de vaga ("Aumento de quadro", etc.) | PDF                       |
| `honorario_novo_colaborador` | Valor do honorário (string)              | PDF (parseado para float) |
| `centro_custo`               | Centro de custo                          | PDF                       |
| `empresa_colaborador_novo`   | Empresa do novo colaborador              | Resolução de empresa      |
| `empresa_solicitante`        | Empresa solicitante                      | PDF                       |
| `nome_responsav_legal`       | Nome do responsável legal                | PDF (assinatura)          |
| `email_responsav_legal`      | Email do responsável                     | PDF                       |
| `funcionario_substituicao`   | Funcionário a ser substituído            | PDF                       |

#### Dados Bancários

| Campo                | Descrição        |
| -------------------- | ---------------- |
| `qual_banco`         | Nome do banco    |
| `tipo_conta`         | Tipo de conta    |
| `agencia_banco`      | Agência          |
| `conta_banco`        | Número da conta  |
| `pix_banco`          | Chave PIX        |
| `titularidade_banco` | Titular da conta |

#### Dados Escolares

| Campo                  | Descrição            |
| ---------------------- | -------------------- |
| `grau_escolaridade`    | Grau de escolaridade |
| `curso_escolaridade`   | Nome do curso        |
| `data_conclusao_facul` | Data de conclusão    |

#### Contatos de Emergência

| Campo                 | Descrição          |
| --------------------- | ------------------ |
| `nome1_emergencia`    | Nome do 1º contato |
| `grau1_parentesco`    | Parentesco         |
| `celular1_emergencia` | Celular            |
| `nome2_emergencia`    | Nome do 2º contato |
| `tipo_relacionamento` | Relacionamento     |
| `celular2_emergencia` | Celular            |

#### Contatos de Emergência

| Campo                 | Descrição          |
| --------------------- | ------------------ |
| `nome1_emergencia`    | Nome do 1º contato |
| `grau1_parentesco`    | Parentesco         |
| `celular1_emergencia` | Celular            |
| `nome2_emergencia`    | Nome do 2º contato |
| `tipo_relacionamento` | Relacionamento     |
| `celular2_emergencia` | Celular            |

#### Checkboxes (Equipamentos e Sistemas)

| Grupo          | Descrição                                                                |
| -------------- | ------------------------------------------------------------------------ |
| `equipamentos` | Dict com checkboxes de equipamentos (ex: `notebook`, `mouse`, `monitor`) |
| `sistemas`     | Dict com checkboxes de sistemas (ex: `email`, `vpn`, `slack`)            |

Valores marcados são identificados por `is_checked()` que verifica se o valor começa com `"[x]"`.

#### Histórico

| Campo                                           | Descrição                                                  |
| ----------------------------------------------- | ---------------------------------------------------------- |
| `consideracoes_historico`                       | Campo de texto livre                                       |
| `consideracoes_historico_historico`             | HTML do histórico de tarefas (com marcadores `{{TAREFA}}`) |
| `consideracoes_historico_historico_complemento` | Complemento do histórico                                   |

#### Dados do ZapSign (após assinatura)

| Campo                     | Descrição                                |
| ------------------------- | ---------------------------------------- |
| `zapsign.link_assinatura` | URL pública do documento para assinatura |
| `zapsign.capturado_em`    | Timestamp da captura do link             |

---

## Modelos de Domínio

### `Enterprise` (Enum)

```python
class Enterprise(Enum):
    FOLHA_TECH = "Folha Tech"
    GENTER = "Genter"
    ARANTES = "Arantes"
```

Método de fábrica `from_string(name)` normaliza o texto (minúsculas, sem acentos) e retorna:

- `"folha" + "tech"` → `FOLHA_TECH`
- `"arantes"` ou `"aaa"` → `ARANTES`
- Qualquer outro → `GENTER` (padrão)

### `Address` (Dataclass)

```python
@dataclass
class Address:
    logradouro: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    cidade: str = ""
    cep: str = ""
```

Propriedade `full_address` concatena todos os campos não vazios com espaços.

### `Candidate` (Dataclass)

```python
@dataclass
class Candidate:
    nome_completo: str          # Obrigatório
    email: Optional[str] = None
    cpf: Optional[str] = None
    rg: Optional[str] = None
    data_nascimento: Optional[str] = None
    estado_civil: Optional[str] = None
    celular: Optional[str] = None
    endereco: Address = field(default_factory=Address)
```

### `Proposal` (Dataclass)

```python
@dataclass
class Proposal:
    candidato: Candidate              # Obrigatório
    empresa: Enterprise               # Obrigatório
    empresa_solicitante: str = ""
    honorario: Optional[float] = None
    tipo_vaga: str = ""
    centro_custo: str = ""
    funcionario_substituicao: str = ""
    equipamentos: list[str] = field(default_factory=list)
    sistemas: list[str] = field(default_factory=list)
    nome_responsavel: str = ""
    email_responsavel: str = ""
    processo_id: Optional[str] = None
    tarefa_nome: Optional[str] = None
    modelo_nome: Optional[str] = None
```

### `Signature` (Dataclass)

```python
@dataclass
class Signature:
    link: str
    capturado_em: str = ""
    nome_signatario: str = ""
    email_signatario: Optional[str] = None
```

---

## Validadores

O módulo `validators.py` fornece funções de limpeza e normalização:

### `normalize_text(s)`

Normaliza texto para busca:

1. Converte para minúsculas
2. Remove acentos (NFD + filtro de categoria Mn)
3. Remove caracteres especiais (exceto letras, números, espaços, hífen)
4. Normaliza espaços múltiplos

**Uso principal**: Busca de PDF por nome do candidato.

### `clean_filename(name)`

Remove caracteres inválidos para nome de arquivo (`/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`),
substitui espaços por `_`, e usa `"Candidato"` como fallback.

### `clean_value(value)`

Limpa valores de formulário:

- Remove `"- selecione algo -"`, `"none"`, `"null"` (case-insensitive)
- Retorna string vazia para valores falsy

### `format_currency(value)`

Formata valor como moeda brasileira:

1. Limpa o valor
2. Remove pontos de milhar, converte vírgula para ponto
3. Formata como `R$ 1.234,56`

### `is_checked(value)` / `clean_checkbox(value)`

- `is_checked`: Verifica se string começa com `"[x]"` (case-insensitive)
- `clean_checkbox`: Remove `"[x]"`, `"[X]"`, `"[ ]"` e retorna texto limpo

### `validate_email(email)`

Validação simples de formato de email (regex `[^@]+@[^@]+\.[^@]+`).

### `validate_not_empty(value, field_name)`

Limpa o valor e levanta `MandatoryFieldError` se vazio.

---

## Tratamento de Erros

Todas as exceções herdam de `AutomationError` (base customizada):

```
AutomationError (Exception)
│
├── TriataError
│   ├── TriataLoginError           — Falha no login do Triata (campo de login ainda visível)
│   ├── TarefaNotFoundError        — Nenhuma tarefa de confecção disponível ou tipo não reconhecido
│   └── FormExtractionError        — Falha ao extrair dados do formulário
│
├── JsonNotFoundError              — Arquivo JSON não encontrado ao carregar
│
├── MandatoryFieldError            — Campo obrigatório ausente ou vazio
│
├── PDFError
│   ├── PDFGenerationError         — Erro genérico na geração de PDF
│   ├── PDFNotFoundError           — PDF não encontrado no diretório
│   └── TemplateNotFoundError     — Arquivo modelo_contrato.txt não encontrado
│
├── ZapSignError
│   ├── ZapSignLoginError          — Falha no login do ZapSign
│   ├── ZapSignUploadError         — Falha no upload de documento ou no viewer
│   └── ZapSignLinkError           — Link inválido ou não capturado após timeout
│
└── BrowserError
    ├── ElementNotFoundError       — Elemento não encontrado no DOM
    └── ClickFailedError           — Todas as 4 estratégias de clique falharam
```

### Comportamento nas Pipelines

Cada workflow (`gerar_proposta` e `enviar_assinatura`) envolve toda a execução em `try/except Exception`:

- Em caso de erro: loga o traceback completo (`logger.exception()`), retorna `None`
- Em caso de sucesso: retorna o caminho do PDF (proposta) ou o link (assinatura)
- O fluxo `completo` (`__main__.py`) interrompe a execução da assinatura se a proposta falhar (`if pdf:`)

---

## Estratégias de Resiliência no Browser

### `safe_click()` — Clique Resiliente

Tenta 4 estratégias em sequência, fechando modais antes de cada tentativa:

1. **Normal**: `btn.click(timeout=5000)`
2. **Force**: `btn.click(force=True, timeout=5000)` — ignora verificação de visibilidade
3. **JavaScript**: `page.evaluate("document.querySelector('...').click()")` — execução direta no DOM
4. **Mouse Event**: Simula eventos `mousemove`, `mousedown`, `mouseup`, `click` via `MouseEvent` com coordenadas calculadas do bounding box

Antes de começar, verifica se o botão está habilitado (loop com deadline de timeout). Se não habilitar, tira screenshot e levanta `ClickFailedError`.

### `close_modal()` — Fechamento de Modal

Até 4 tentativas de fechamento:

1. `click()` normal
2. `click(force=True)`
3. `dispatch_event("click")`
4. `page.evaluate("el.click()")` via element_handle

Se ainda visível, **remove do DOM** via JavaScript:

- Altera `display`, `visibility`, `opacity`
- Remove elementos com classes `.cdk-overlay-backdrop`, `.modal-backdrop`, `.overlay`, `.backdrop`

### `safe_fill()` — Preenchimento Resiliente

1. Fecha modais
2. Aguarda elemento visível
3. Clica no campo
4. Preenche com `fill()`

### `wait_for_value()` — Aguardar Valor

Usa `page.wait_for_function()` para aguardar uma condição JavaScript no valor de um input.

### `click_canvas_center()` — Clique no Canvas

Para elementos canvas (renderização de PDF no ZapSign):

1. Tenta `click()` normal
2. Tenta `click(force=True)`
3. Calcula bounding box e usa `page.mouse.click()` no centro

### `scroll_viewer_to_bottom()` — Scroll no Viewer

Scrolla iterativamente (até 55 passos) até a última página do viewer, com pausa de 350ms entre passos.

### `wait_for_spinners()` — Aguardar Spinners

Aguarda 2s fixos, fecha modais, e aguarda ocultação de seletores comuns de loading:

- `.mat-progress-spinner`
- `.mat-spinner`
- `.loading`
- `.loader`
- `[aria-busy='true']`

---

## Anti-Detecção do Browser

Para evitar detecção como bot, o `browser/factory.py` aplica múltiplas técnicas:

### 1. Argumentos de Lançamento

```python
args=[
    "--start-maximized",
    "--disable-blink-features=AutomationControlled",
]
```

### 2. Script de Inicialização

```python
context.add_init_script(
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
)
```

Isso remove a flag `navigator.webdriver` que muitos sites usam para detectar automação.

### 3. User-Agent Customizado

```
Mozilla/5.0 (Windows NT 10.0; Win64; x64)
AppleWebKit/537.36 (KHTML, like Gecko)
Chrome/124.0.0.0 Safari/537.36
```

### 4. Viewport Realista

1920×1080, o padrão mais comum de desktop.

### 5. Locale

`pt-BR` para formatação de datas, números e moeda consistente com o Brasil.

### 6. HTTPS

`ignore_https_errors=True` — necessário para ambientes de desenvolvimento com certificados auto-assinados.

---

## Logging

Configurado em `logging_config.py`:

### Formato

```
HH:MM:SS  [LEVEL  ]  mensagem
```

Exemplo:

```
12:34:56  [INFO   ]  Acessando Triata...
12:34:57  [WARNING]  PDF pelo nome não encontrado. Usando o mais recente.
12:34:58  [ERROR  ]  Falha ao gerar proposta.
```

### Níveis

- **INFO**: Fluxo principal, sucesso, estados
- **WARNING**: Fallbacks, condições inesperadas mas recuperáveis
- **ERROR**: Falhas de pipeline (retorna None)
- **DEBUG**: Detalhes de preenchimento de campos (suprimido por padrão)

### Supressão de Libs Ruidosas

Os loggers de bibliotecas são suprimidos para WARNING:

- `urllib3`
- `playwright`
- `asyncio`

### Nome dos Loggers

Todos os loggers usam o prefixo `automacao.`:

- `automacao.main` — CLI dispatcher
- `automacao.workflow.gerar_proposta` — Pipeline 1
- `automacao.workflow.enviar_assinatura` — Pipeline 2
- `automacao.triata` — Interações com Triata
- `automacao.zapsign` — Interações com ZapSign
- `automacao.browser` — Ações genéricas de browser

---

## Persistência

### JSON (`dados_formulario_atual.json`)

- **Formato**: UTF-8, indentação 4 espaços, sem escape ASCII
- **Comportamento**: **Sobrescrito** a cada execução da pipeline de proposta
- **Conteúdo**: Dict completo com todos os campos extraídos do Triata + metadados
- **Atualização**: Após assinatura, adiciona chave `zapsign` com `link_assinatura` e `capturado_em`

Funções disponíveis (`json_repository.py`):

| Função                                   | Descrição                                                                                       |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `load(path)`                             | Carrega e retorna dict. Levanta `JsonNotFoundError` se não existir.                             |
| `save(path, data)`                       | Salva dict como JSON.                                                                           |
| `update(path, updates)`                  | Carrega, mescla com updates, salva.                                                             |
| `save_signature_link(path, link)`        | Adiciona `zapsign.link_assinatura` e `zapsign.capturado_em`.                                    |
| `get_field(path, field, required=False)` | Retorna valor de um campo específico. Levanta `MandatoryFieldError` se `required=True` e vazio. |

### Excel (`dados_formularios.xlsx`)

- **Formato**: `.xlsx` via openpyxl
- **Comportamento**: **Append** (não sobrescreve)
- **Planilha**: Nomeada "Dados"
- **Estrutura**: Cabeçalho automático a partir das chaves do primeiro dict

**Flattening**: Chaves aninhadas são achatadas com underscore. Exemplo:

```python
# Input:
{"equipamentos": {"notebook": "[x] Notebook", "mouse": "[ ] Mouse"}}

# Output no Excel:
# equipamentos_notebook | equipamentos_mouse
# "[x] Notebook"        | "[ ] Mouse"
```

### PDFs (`pdfs_gerados/`)

- **Criação automática**: O diretório é criado automaticamente se não existir (`mkdir(parents=True, exist_ok=True)`)
- **Nomenclatura**:
  - `Carta_Proposta_{NOME_SANITIZADO}.pdf`
  - `Contrato_{NOME_SANITIZADO}.pdf`
- **Sanitização**: Caracteres inválidos para filename são substituídos por `_`

---

## Troubleshooting

### Erro: `TarefaNotFoundError` — Nenhuma tarefa de confecção disponível

**Causas possíveis:**

- Não há tarefas de confecção (04.1 ou 08) na fila do usuário `robo.cadastro`
- O usuário `robo.cadastro` não tem permissão para ver a tarefa
- O seletor CSS `td[id^="tarefa_"]` mudou no Triata

**Soluções:**

1. Verifique manualmente se há tarefas no Triata para o usuário
2. Confirme que o usuário tem permissão de acesso
3. Verifique se o HTML do Triata mudou (inspecionar via DevTools)

### Erro: `TriataLoginError` — Campo de login ainda visível

**Causas:**

- Credenciais inválidas
- Sistema Triata fora do ar ou lento
- Modal de manutenção bloqueando

**Soluções:**

1. Verifique `TRIATA_USERNAME` e `TRIATA_PASSWORD` em `settings.py`
2. Aumente `LOGIN_TIMEOUT` (ex: 60.000ms)
3. Verifique se há alertas ou modais no login

### Erro: `MandatoryFieldError` — ZAPSIGN_EMAIL não definido

**Causa:**

- `.env` não existe ou não contém as variáveis

**Solução:**

```bash
# Verifique se o arquivo existe
cat .env

# Deve conter:
ZAPSIGN_EMAIL=seu@email.com
ZAPSIGN_PASSWORD=sua_senha
```

### Erro: Nenhum PDF encontrado

**Causas:**

- Pipeline de proposta não foi executada antes
- PDF foi movido/deletado de `pdfs_gerados/`
- Nome do candidato no JSON não corresponde ao nome do arquivo

**Soluções:**

1. Execute a proposta primeiro: `uv run python -m automation proposta`
2. Verifique se o PDF existe em `pdfs_gerados/`
3. O sistema usa fallback para o PDF mais recente, então verifique se o nome do candidato corresponde

### Erro: `ZapSignUploadError` — Nenhuma página no viewer

**Causas:**

- Upload falhou (arquivo corrompido ou muito grande)
- ZapSign mudou a interface do viewer
- Timeout de upload muito curto

**Soluções:**

1. Verifique o tamanho do PDF (deve ser < 10MB tipicamente)
2. Aumente `UPLOAD_TIMEOUT` (ex: 300.000ms)
3. Verifique se os seletores no `zapsign_client.py` ainda correspondem à interface

### Erro: `ZapSignLinkError` — Link inválido

**Causas:**

- O documento não foi enviado corretamente
- A interface do ZapSign mudou (o seletor `input.signer_link` não existe mais)
- Timeout muito curto para geração do link

**Soluções:**

1. Verifique se o documento aparece na dashboard do ZapSign
2. Aumente o timeout de `capture_link()` (ex: 180.000ms)
3. Inspecione a interface do ZapSign para verificar se o seletor mudou

### PDF gerado sem logo

**Causa:**

- Diretório `Logos/<Empresa>/` não existe ou está vazio

**Solução:**

```
Logos/
├── Folha Tech/
│   └── logo.png      # ← Adicione aqui
├── Genter/
│   └── logo.jpg      # ← Adicione aqui
└── Arantes/
    └── logo.png      # ← Adicione aqui
```

### PDF de contrato com placeholders não substituídos

**Causa:**

- `modelo_contrato.txt` não existe ou o placeholder está escrito incorretamente
- O nome do campo no placeholder não corresponde ao nome do campo no JSON

**Solução:**

1. Verifique se `modelo_contrato.txt` existe na raiz
2. Os placeholders devem usar `{{nome_exato_do_campo}}` (ex: `{{nome_completo}}`)
3. Verifique os nomes dos campos no `dados_formulario_atual.json`

### Execução muito lenta

**Causas:**

- `SLOW_MO` muito alto (padrão: 50ms)
- Rede lenta
- Timeouts muito longos

**Soluções:**

1. Reduza `SLOW_MO` para 0 (ou comente) em `settings.py`
2. Verifique a conectividade com `workflow.folhatech.com.br` e `app.zapsign.com.br`
3. Considere executar em ambiente com melhor banda

### Modais bloqueando interações

**Causa:**

- O ZapSign ou Triata exibem modais de boas-vindas, cookies, ou avisos

**Solução:**

- A função `close_modal()` já tenta lidar com isso, mas se o modal mudar:
  - Atualize o seletor em `close_modal()` (`button[aria-label='Fechar modal']`)
  - Ou adicione o seletor do novo modal

---

## Exemplos de Saída

### Execução de Proposta (tarefa 04.1)

```
10:41:31  [INFO   ]  === PIPELINE 1: Gerar Proposta ===
10:41:32  [INFO   ]  Acessando Triata...
10:41:35  [INFO   ]  Preenchendo login...
10:41:35  [INFO   ]  Preenchendo senha...
10:41:36  [INFO   ]  Clicando em Entrar...
10:41:38  [INFO   ]  Login realizado. URL: https://workflow.folhatech.com.br/triata/Sistema.php?area=Processo
10:41:38  [INFO   ]  Aguardando listagem de tarefas...
10:41:40  [INFO   ]  Encontradas 3 tarefas.
10:41:40  [INFO   ]  Tarefa: 04.1 - Confecção Proposta | Processo: 22133
10:41:40  [INFO   ]  Formulário carregado.
10:41:41  [INFO   ]  Total de 45 campos extraídos.
10:41:41  [INFO   ]  Dados salvos em JSON e Excel.
10:41:42  [INFO   ]  PDF da carta proposta gerado: C:\...\pdfs_gerados\Carta_Proposta_Alex_de_Niteroi.pdf
10:41:42  [INFO   ]  Navegador fechado.
```

### Execução de Assinatura

```
10:41:43  [INFO   ]  === PIPELINE 2: Enviar para Assinatura ===
10:41:43  [INFO   ]  Candidato: Alex de Niterói | Email: pedro.santana@folhatech.com.br
10:41:43  [INFO   ]  PDF para upload: C:\...\pdfs_gerados\Carta_Proposta_Alex_de_Niteroi.pdf
10:41:44  [INFO   ]  Acessando ZapSign...
10:41:46  [INFO   ]  Login ZapSign confirmado.
10:41:46  [INFO   ]  Criando documento...
10:41:48  [INFO   ]  Aguardando input de upload...
10:41:48  [INFO   ]  Enviando PDFs: ['C:\...\pdfs_gerados\Carta_Proposta_Alex_de_Niteroi.pdf']
10:41:50  [INFO   ]  Aguardando processamento...
10:41:52  [INFO   ]  Clicando Continuar...
10:41:53  [INFO   ]  Ativando autenticação avançada...
10:41:54  [INFO   ]  Autenticação avançada ativada.
10:41:54  [INFO   ]  Preenchendo signatário: Alex de Niterói
10:41:55  [INFO   ]  Signatário preenchido.
10:41:55  [INFO   ]  Clicando em Enviar...
10:41:57  [INFO   ]  Documento enviado.
10:41:57  [INFO   ]  Aguardando viewer do PDF...
10:42:00  [INFO   ]  Total de páginas: 2
10:42:00  [INFO   ]  Visto aplicado na página 1
10:42:01  [INFO   ]  Visto aplicado na página 2
10:42:02  [INFO   ]  Viewers encontrados: 1
10:42:03  [INFO   ]  Processando viewer 1/1
10:42:05  [INFO   ]  Assinatura inserida no viewer 1
10:42:06  [INFO   ]  Aguardando link de assinatura...
10:42:10  [INFO   ]  Link capturado: https://app.zapsign.com.br/ver/abc123def456
10:42:10  [INFO   ]  Link de assinatura salvo no JSON.
10:42:10  [INFO   ]  Navegador fechado.
```

### JSON Resultante (após completo)

```json
{
  "extraido_em": "05/06/2026, 10:41:31",
  "url": "https://workflow.folhatech.com.br/triata/Sistema.php",
  "processo_id": "22133",
  "tarefa_nome": "04.1 - Confecção Proposta",
  "modelo_nome": "Arantes - Contratação PJ",
  "nome_completo": "Alex de Niterói",
  "email_pessoal_candidato": "pedro.santana@folhatech.com.br",
  "cpf_candidato": "042.815.546-45",
  "honorario_novo_colaborador": "3500.00",
  "tipo_vaga": "Aumento de quadro",
  "centro_custo": "TI",
  "empresa_colaborador_novo": "Folha Tech",
  "nome_responsav_legal": "Fernando Andrade (Folha Tech)",
  "email_responsav_legal": "fernando.andrade@folhatech.com.br",
  "endereco_completo": "etetetet",
  "numero_endereco": "124",
  "complemento_endereco": "fwfwee",
  "cep_prestador": "43242-523",
  "bairro_prestador": "wrwrwrw",
  "cidade_prestador": "são paulo",
  "equipamentos": {
    "notebook": "[x] Notebook Dell",
    "mouse": "[x] Mouse Logitech",
    "monitor": "[ ] Monitor"
  },
  "sistemas": {
    "email": "[x] Email corporativo",
    "vpn": "[x] VPN",
    "slack": "[ ] Slack"
  },
  "zapsign": {
    "link_assinatura": "https://app.zapsign.com.br/ver/abc123def456",
    "capturado_em": "2024-06-05 10:42:10"
  }
}
```

---

## Considerações de Segurança

### Credenciais

- **Triata**: Credenciais (`robo.cadastro` / `Robo@aut2024`) estão hardcoded em `settings.py`. Não são dados sensíveis de usuário humano, mas ainda assim devem ser protegidos.
- **ZapSign**: Credenciais **devem** estar no `.env`, nunca no código. O `.env` está no `.gitignore`.

### Dados dos Candidatos

- CPFs, RG, endereços, dados bancários e contatos de emergência são extraídos e armazenados em `dados_formulario_atual.json` e `dados_formularios.xlsx`.
- **Esses arquivos contêm dados pessoais sensíveis** e devem ser protegidos conforme a LGPD.
- Recomenda-se:
  - Não commitar os arquivos de dados (já ignorados via `.gitignore`? — verificar)
  - Restringir acesso ao diretório do projeto
  - Considerar criptografia dos arquivos JSON/Excel em ambientes de produção

### Links de Assinatura

- Links do ZapSign são URLs públicas (acessíveis por qualquer pessoa com o link).
- **Não compartilhe links publicamente**.
- O link é salvo no JSON local; garanta que o arquivo tenha permissões restritas.

### Anti-Detecção

- O projeto usa técnicas de anti-detecção (`navigator.webdriver = undefined`, user-agent customizado).
- Essas técnicas são legítimas para automação de sistemas próprios, mas **não devem ser usadas para violar Termos de Serviço** de terceiros.

---

## Desenvolvimento

### Estrutura de Importação

O projeto usa imports absolutos a partir do pacote `automation`:

```python
from automation.src.config import settings
from automation.src.domain.models import Proposal, Candidate
from automation.src.infrastructure.browser.factory import create_page
```

### Executar um Módulo Específico

```bash
# Executar apenas o workflow de proposta
uv run python -c "from automation.src.application.workflows import gerar_proposta; gerar_proposta()"

# Executar apenas o serviço de branding
uv run python -c "from automation.src.application.services.branding_service import get_theme; print(get_theme(...))"
```

### Modificar Timeouts

Edite `automation/src/config/settings.py` ou defina variáveis de ambiente:

```bash
# Linux/macOS
export DEFAULT_TIMEOUT=60000
export SLOW_MO=100

# Windows PowerShell
$env:DEFAULT_TIMEOUT = "60000"
$env:SLOW_MO = "100"
```

### Modificar o Template de Contrato

Edite `modelo_contrato.txt` na raiz do projeto. Use placeholders no formato `{{nome_do_campo}}`:

```
CONTRATO DE PRESTAÇÃO DE SERVIÇOS

Contratante: {{empresa_solicitante}}
Contratado: {{nome_completo}}
CPF: {{cpf_candidato}}

Honorários: {{honorario_novo_colaborador}}

Data: {{amb_data_hora_formatada}}
```

Campos com "honorario" ou "valor" no nome são automaticamente formatados como `R$ 1.234,56`.

### Adicionar uma Nova Empresa

1. Adicione ao enum em `automation/src/domain/models.py`:

   ```python
   class Enterprise(Enum):
       # ... existentes
       NOVA_EMPRESA = "Nova Empresa"
   ```

2. Atualize `from_string()` para reconhecer a nova empresa.

3. Adicione o tema em `automation/src/application/services/branding_service.py`:

   ```python
   Enterprise.NOVA_EMPRESA: {
       "primaria": "#FF0000",
       "secundaria": "#FFCCCC",
       "texto": "#333333",
   }
   ```

4. Adicione a imagem de assinatura:

   ```python
   Enterprise.NOVA_EMPRESA: "AssNovaEmpresa.png"
   ```

5. Crie o diretório de logo: `Logos/Nova Empresa/`

---

## Manutenção

### Atualizar Dependências

```bash
uv sync --upgrade
```

### Verificar Versão do Python

```bash
python --version  # Deve ser >= 3.12
```

### Reinstalar Playwright Browsers

```bash
uv run playwright install chromium
```

### Limpar Dados de Teste

```bash
# Remove JSON e Excel gerados
rm dados_formulario_atual.json dados_formularios.xlsx

# Remove PDFs
rm -rf pdfs_gerados/*
```

---

## CI / Qualidade

CI em `.github/workflows/ci.yml` (GitHub Actions, Ubuntu, Python 3.12):

```bash
uv lock --check                    # verificar lock file
uv sync --all-extras --dev         # instalar deps + dev
uv run ruff check .                # lint
uv run ruff format --check .       # checar formatação
uv run mypy automation/            # type check
uv run python -c "import automation; print('Import OK')"  # importação
```

**Ruff** (`pyproject.toml`): line-length 100, double quotes, space indent, regras E/F/I/W/UP.  
**Mypy**: `strict = false`, ignora imports faltantes de `reportlab.*`, `playwright.*`, `pandas.*`, `openpyxl.*`, `pydantic_settings.*`.

Instalar dev tools localmente:

```bash
uv sync --all-extras --dev
```

---

## Limitações Conhecidas

1. **Sem Testes Automatizados**: Não há suíte de testes (unitários, integração ou e2e). Qualquer mudança requer validação manual.

2. **Dependência de Seletores CSS**: O Triata e ZapSign podem mudar seus HTMLs a qualquer momento. Seletores hardcoded podem quebrar.

3. **Primeira Tarefa Sempre**: O sistema sempre pega a **primeira** tarefa da lista. Se a ordem não for a esperada, processará o candidato errado.

4. **Sem Fila de Processamento**: Não há mecanismo de fila. Se houver múltiplas tarefas, é necessário executar múltiplas vezes.

5. **Execução Sequencial**: Não há paralelismo. Cada candidato é processado um por vez.

6. **PDF de Contrato Simples**: O template de contrato é um texto simples com substituição de placeholders. Não suporta layouts complexos, tabelas ou condicionais.

7. **Resolução de Empresa por Heurística**: `Enterprise.from_string()` usa matching por substring. Empresas com nomes similares podem ser classificadas incorretamente.

8. **Sem Retry Automático**: Se uma etapa falhar (ex: timeout de rede), toda a pipeline falha. Não há mecanismo de retry com backoff.

9. **Logs Somente em Console**: Não há persistência de logs em arquivo. Se o terminal for fechado, os logs são perdidos.

10. **Sem Notificação**: Após a execução, o sucesso/falha não é notificado por email, Slack, etc. O operador deve verificar o terminal manualmente.

---

## Licença

Uso interno — **Folha Tech / Genter / Arantes**.

Este projeto é propriedade intelectual das empresas do grupo e não deve ser distribuído externamente sem autorização.
