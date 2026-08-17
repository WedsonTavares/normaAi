# ARCHITECTURE.md — NormaAI

Este documento descreve a **arquitetura atual válida**. Não é histórico de decisões.
Autoridade superior: `CLAUDE.md`.

---

## 1. Visão geral

O backend concentra toda a lógica. Frontend e n8n são apenas clientes HTTP dele:

```
┌──────────────────────┐        HTTP/JSON        ┌──────────────────────┐
│  frontend (Vite)     │ ──────────────────────► │  backend (FastAPI)   │
│  React + TS + Tailwind│ ◄────────────────────── │  Python 3.12         │
└──────────────────────┘                          └──────────┬───────────┘
┌──────────────────────┐                                     │
│  n8n (automação)     │ ───────────────────────────────────►│
│  agenda e monitora   │                                     │
└──────────────────────┘                                     │
                                        ┌────────────────────┼────────────────────┐
                                        ▼                    ▼                    ▼
                                 ┌─────────────┐      ┌─────────────┐     ┌─────────────┐
                                 │  PostgreSQL │      │  OpenAI API │     │ disco local │
                                 │  + pgvector │      │  embeddings │     │  PDFs       │
                                 │  (Supabase) │      │  + chat     │     │             │
                                 └─────────────┘      └─────────────┘     └─────────────┘
```

O frontend **nunca** fala com a OpenAI nem com o banco. Toda credencial vive no backend.
O n8n também não fala com banco nem com OpenAI: ele só chama a API do backend.

---

## 2. Estrutura de diretórios

```
normaAi/
├── CLAUDE.md
├── docker-compose.yml          # Postgres+pgvector local (alternativa ao Supabase em dev)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUSINESS_RULES.md
│   ├── DATABASE.md
│   ├── ROADMAP.md
│   └── ai/                     # prompts dos papéis (orchestrator, architect, impl, review)
├── backend/
│   ├── app/
│   │   ├── main.py             # criação do app, middlewares, handlers, routers
│   │   ├── api/                # rotas HTTP — finas
│   │   ├── schemas/            # contratos Pydantic de entrada/saída
│   │   ├── services/           # regras de negócio e integrações
│   │   ├── core/               # config, logging, erros
│   │   ├── database/           # conexão, SQL e migrações
│   │   └── tests/              # pytest
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml          # ruff + pytest + mypy
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/           # única camada que faz HTTP
│   │   ├── hooks/
│   │   ├── types/
│   │   └── lib/
│   ├── package.json
│   └── .env.example
└── normaai-n8n/
    ├── DOC.md                  # workflows e contratos consumidos
    ├── .env.n8n.example
    └── workflows/              # JSONs exportados do n8n
```

Os diretórios do frontend são criados conforme a necessidade real de cada fase — a estrutura
acima é o destino, não um conjunto de pastas vazias a criar antecipadamente.

Regra de dependência no backend: `api → services → database / integrações`.
`core` e `schemas` podem ser importados por qualquer camada. Services **não** importam de `api`.

---

## 3. Backend

### 3.1 Camadas

| Camada      | Responsabilidade                                                      | Não faz                            |
| ----------- | --------------------------------------------------------------------- | ---------------------------------- |
| `api/`      | validar entrada, chamar service, devolver schema                      | regra de negócio, SQL, chamada IA  |
| `services/` | regra de negócio, orquestração do fluxo, integrações externas         | conhecer `Request`/`Response` HTTP |
| `database/` | conexão e SQL                                                          | regra de negócio                   |
| `schemas/`  | contratos Pydantic                                                     | lógica                             |
| `core/`     | configuração, logging, tipos de erro                                   | regra de negócio                   |

### 3.2 Configuração

`app/core/config.py` — `Settings` com `pydantic-settings`, carregado de variáveis de ambiente
e de `.env` em desenvolvimento. Instância única via `get_settings()` com `lru_cache`.
Nenhum `os.getenv` espalhado pelo código.

As rotas recebem a configuração por injeção (`Depends(get_settings)`), nunca chamando
`get_settings()` diretamente — é isso que permite `create_app(settings)` nos testes.

### 3.3 Erros

Toda a API responde erro no mesmo formato:

```json
{ "error": { "code": "not_found", "message": "Recurso não encontrado." } }
```

- `app/core/errors.py` define `AppError` e as subclasses concretas `InvalidInputError` (400),
  `NotFoundError` (404) e `ExternalServiceError` (502).
- `register_error_handlers(app)` registra quatro handlers:
  - `AppError` → status e código próprios do erro;
  - `StarletteHTTPException` → erros gerados pelo framework (404, 405);
  - `RequestValidationError` → 422 informando **quais campos** são inválidos, sem ecoar o valor recebido;
  - `Exception` → log com traceback + resposta 500 genérica.
- Convenção: regras da aplicação levantam `AppError`, nunca `HTTPException`.
- O usuário nunca recebe stack trace, SQL ou credencial.

### 3.4 Logging

`logging` da biblioteca padrão, configurado uma única vez em `app/core/logging.py`.
Formato: `timestamp | level | logger | mensagem`. Nível vem de `LOG_LEVEL`.
Toda falha de integração externa loga: operação, identificador do recurso e causa.

### 3.5 Processamento de documentos

O processamento (extração de texto → extração estruturada → chunking → embeddings) é
disparado com `BackgroundTasks` do próprio FastAPI, e o estado é acompanhado pela coluna
`documents.status`. O frontend faz *polling* da listagem/detalhe.

**Por que não uma fila:** o volume do MVP é baixo e uma fila distribuída (Celery/Redis) está
explicitamente fora de escopo. `BackgroundTasks` resolve o requisito atual sem infraestrutura
adicional. Se o processamento passar a exigir retry automático, paralelismo ou durabilidade
entre reinícios, a decisão deve ser reavaliada pelo papel de Arquitetura.

Como o disparo é assíncrono, `POST /api/documents/{id}/process` responde imediatamente com o
status corrente e **é idempotente**: chamar de novo enquanto o documento está `processing` não
inicia um segundo processamento (RN-08). Isso é o que torna seguro qualquer cliente repetir a
chamada — inclusive o n8n.

### 3.6 Convenção de rotas

| Prefixo | Uso                                                                 |
| ------- | ------------------------------------------------------------------- |
| `/api`  | todas as rotas de recurso (`/api/documents`, `/api/search`, `/api/ask`, …) |
| raiz    | apenas `GET /health`, para que o monitoramento não dependa do prefixo |

Os routers de recurso são montados com `prefix="/api"` no `main.py`. `health` é montado na raiz.

---

## 4. Acesso a dados

**Decisão: SQL explícito com `psycopg` 3 + pool de conexões. Sem ORM.**

Justificativa:
- a busca vetorial com pgvector exige SQL de qualquer forma;
- o schema é pequeno (5 tabelas) e estável;
- SQL explícito é mais fácil de ler, testar e depurar do que camadas de ORM;
- evita a abstração `repository`, proibida sem necessidade concreta pelo `CLAUDE.md`.

`app/database/connection.py` expõe o pool e um context manager de conexão.
As consultas ficam junto do service que as usa, em funções pequenas e nomeadas.

Migrações são arquivos `.sql` numerados em `backend/app/database/migrations/`, aplicados por
um script simples (`python -m app.database.migrate`) que registra o que já rodou.
Sem ferramenta de migração externa enquanto o schema couber nesse modelo.

---

## 5. Integração com IA

Um módulo por responsabilidade, todos em `services/`:

**Dois provedores**, porque o DeepSeek não expõe endpoint de embeddings:

| Uso                              | Provedor | Modelo                   |
| -------------------------------- | -------- | ------------------------ |
| Extração estruturada e RAG       | DeepSeek | `deepseek-v4-pro`        |
| Embeddings                       | OpenAI   | `text-embedding-3-small` |

Ambos falam o protocolo da OpenAI, então o mesmo SDK atende os dois — muda só a `base_url`.

| Módulo                  | Responsabilidade                                                |
| ----------------------- | --------------------------------------------------------------- |
| `llm_client.py`         | criação dos dois clientes, timeout e tradução de erro            |
| `embedding_service.py`  | gerar embeddings em lote                                         |
| `extraction_service.py` | extração estruturada e validação da saída                        |
| `rag_service.py`        | retrieval + montagem de contexto + resposta com citações         |

**`deepseek-v4-pro` é um modelo de raciocínio.** Os tokens de raciocínio contam no orçamento
de saída: com `max_tokens` curto a resposta volta **vazia**, sem erro. Por isso a extração usa
`max_tokens=4000`.

**Sem `json_schema` estrito.** O DeepSeek suporta apenas `response_format: json_object`, que
garante JSON válido mas não garante o formato. O schema é imposto do nosso lado: o payload
passa por `ExtractedDocument` (Pydantic) e saída fora do contrato é falha da etapa (RN-12).

Regras:
- modelo e dimensão de embedding vêm de configuração, nunca hardcoded no meio da lógica;
- toda chamada tem timeout explícito;
- falha da OpenAI vira `ExternalServiceError` com log da causa real e mensagem genérica ao usuário;
- a saída estruturada é **sempre** validada por um modelo Pydantic antes de ser persistida.

**Decisão: LlamaIndex não será utilizado.** Chunking, embeddings e retrieval sobre pgvector
somam poucas dezenas de linhas de código direto e explícito. Introduzir o framework adicionaria
abstrações e uma dependência pesada sem resolver problema concreto — contrariando o `CLAUDE.md`.
A decisão será revista se surgir necessidade real (ex.: múltiplas estratégias de retrieval).

---

## 6. RAG

```
pergunta
  → embedding da pergunta
  → busca por similaridade de cosseno em document_chunks (top-k, filtro opcional por documento)
  → montagem de contexto numerado com metadados (documento, página, artigo)
  → chamada ao modelo de chat com instrução de citar apenas as fontes fornecidas
  → resposta + lista de fontes (chunk_id, documento, página, artigo, trecho)
```

- Modelo: `text-embedding-3-small` (1536 dimensões) para embeddings.
- Similaridade: operador `<=>` (cosseno) do pgvector.
- A resposta da API sempre devolve as fontes efetivamente recuperadas — o frontend exibe o
  trecho original ao lado da resposta, permitindo verificação humana.
- Se nenhum chunk relevante for recuperado, o backend responde explicitamente que não há
  base nos documentos, sem chamar o modelo de geração.

---

## 7. Armazenamento de arquivos

PDFs são gravados em disco, em diretório configurável (`STORAGE_DIR`), com nome derivado do
hash do conteúdo. O caminho é registrado em `documents.storage_path`.

**Limitação conhecida e aceita no MVP:** disco local não persiste em containers efêmeros.
Migrar para Supabase Storage é uma alteração isolada em um único service, a ser feita apenas
quando houver deploy que exija isso.

---

## 8. Frontend

- Vite + React + TypeScript + Tailwind CSS.
- `services/api.ts` é a **única** camada que faz HTTP; devolve tipos declarados em `types/`.
- Componentes tratam obrigatoriamente três estados: carregando, erro e vazio.
- Sem lógica de negócio relevante em componente — cálculo e transformação ficam em `lib/` ou `hooks/`.
- Nenhuma chave de API no frontend. A única variável de ambiente é `VITE_API_URL`.

Páginas do MVP: Documentos (upload + lista), Detalhe do documento, Busca, Perguntas (RAG), Avaliação.

---

## 9. Automação (n8n)

O n8n é um **cliente da API**, no mesmo nível do frontend. Ele nunca acessa banco, OpenAI ou
disco, e nunca implementa regra de negócio.

```
n8n decide QUANDO executar. O backend sabe COMO executar.
```

Workflows em `normaai-n8n/workflows/`, documentados em `normaai-n8n/DOC.md`:

| Workflow                    | Gatilho              | Endpoint consumido                     |
| --------------------------- | -------------------- | -------------------------------------- |
| 01 — processar documento    | Webhook              | `POST /api/documents/{id}/process`     |
| 02 — avaliar RAG            | Schedule diário      | `POST /api/evaluations/run`            |
| 03 — monitorar API          | Schedule 5 min       | `GET /health`                          |
| 04 — error handler          | Error Trigger        | `POST /api/operations/n8n-errors`      |

Regras:
- os workflows leem a URL do backend de `NORMAAI_API_URL`; nenhuma URL fica fixa no JSON;
- nenhum segredo é gravado no JSON do workflow;
- o workflow 04 é o Error Workflow dos demais e **não pode falhar**: o node que registra o
  erro está configurado para continuar mesmo se o endpoint estiver fora, evitando erro em cascata;
- endpoints chamados por automação precisam ser idempotentes ou não ter retry configurado.

**Por que n8n e não um cron no backend:** agendamento, histórico de execuções e captura de
falhas já vêm prontos e ficam fora do código do produto. O backend continua sem nenhuma
dependência do n8n — se o n8n estiver desligado, a aplicação funciona igual.

---

## 10. Configuração e ambiente

Toda configuração sensível vem de variáveis de ambiente. `backend/.env.example`,
`frontend/.env.example` e `normaai-n8n/.env.n8n.example` documentam as variáveis,
sempre sem valores reais.

Variáveis do backend: `DATABASE_URL`, `OPENAI_API_KEY`, `OPENAI_EMBEDDING_MODEL`,
`OPENAI_CHAT_MODEL`, `STORAGE_DIR`, `LOG_LEVEL`, `CORS_ORIGINS`, `MAX_UPLOAD_MB`.

`docker-compose.yml` sobe apenas Postgres com pgvector para desenvolvimento local, como
alternativa ao Supabase. Backend e frontend rodam nativamente em dev.

---

## 11. Testes

- Backend: `pytest`. Prioridade para services, chunking, retrieval, validação de saída da IA
  e contratos das rotas. OpenAI e banco são substituídos por dublês nos testes unitários.
- Frontend: testes apenas onde houver lógica que justifique.
- Qualidade: `ruff` (lint + format) e `mypy` no backend; `tsc --noEmit` e `eslint` no frontend.
