# NormaAI

Aplicação para ler, estruturar, indexar e consultar documentos legais e normativos usando IA.

Envie um PDF de uma norma e o sistema extrai o texto, identifica os dados estruturados
(órgão, tipo, data, obrigações, prazos), divide o conteúdo por artigo, gera embeddings e
permite perguntar em linguagem natural — **sempre respondendo com o trecho original citado**,
para que a resposta possa ser conferida.

```
upload de PDF → extração de texto → extração estruturada → chunking por artigo
→ embeddings → pgvector → busca semântica → RAG → resposta com artigo e página citados
→ avaliação da qualidade do retrieval
```

## Stack

| Camada    | Tecnologia                                      |
| --------- | ----------------------------------------------- |
| Frontend  | React, TypeScript, Vite, Tailwind CSS           |
| Backend   | Python 3.12, FastAPI, Pydantic                  |
| Banco     | PostgreSQL + pgvector (Supabase ou local)       |
| IA        | OpenAI — embeddings e Structured Outputs        |
| Testes    | Pytest, Vitest                                  |
| Automação | n8n para agendamento e monitoramento            |

## Como rodar

Pré-requisitos: Python 3.12, Node 20+, Docker (ou uma instância Supabase).

**1. Banco**

```bash
docker-compose up -d db
```

**2. Backend**

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env          # preencha OPENAI_API_KEY e DATABASE_URL
.venv/bin/python -m app.database.migrate
.venv/bin/python -m uvicorn app.main:app --reload
```

**3. Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Backend em `http://localhost:8000` (docs em `/docs`), frontend em `http://localhost:5173`.

## Testes e qualidade

```bash
cd backend  && .venv/bin/python -m pytest && .venv/bin/python -m ruff check . && .venv/bin/python -m mypy
cd frontend && npm test && npm run typecheck && npm run lint && npm run build
```

Os testes que dependem de banco são pulados automaticamente quando `TEST_DATABASE_URL`
não está definida, então a suíte roda em qualquer máquina.

## Decisões técnicas

Algumas escolhas que valem explicação, porque o caminho mais popular nem sempre foi o adotado:

**Sem LlamaIndex / LangChain.** Chunking, embeddings e busca por similaridade sobre pgvector
somam poucas dezenas de linhas de código direto. Um framework de RAG traria abstrações e uma
dependência pesada para resolver algo que o SQL e o SDK da OpenAI já resolvem — e tornaria
mais difícil responder "por que este trecho foi recuperado?". A decisão é revisada se surgir
necessidade real, como múltiplas estratégias de retrieval concorrentes.

**Sem ORM.** A busca vetorial exige SQL de qualquer forma, o schema tem cinco tabelas e é
estável. SQL explícito é mais fácil de ler e depurar do que camadas de mapeamento.

**Processamento com `BackgroundTasks`, não fila.** O volume do MVP é baixo. Celery e Redis
resolveriam um problema que ainda não existe. O estado é acompanhado por `documents.status`.

**Endpoint de processamento idempotente.** Pedir processamento de um documento que já está
`processing` devolve o status atual em vez de iniciar um segundo processamento. Sem isso, um
duplo clique ou um retry automático duplicaria chunks, embeddings e custo de API.

**Citação vem do banco, nunca do modelo.** As fontes exibidas são os chunks efetivamente
recuperados. Referência que o modelo mencione e que não exista entre esses chunks não é
apresentada como fonte — é o que impede citação inventada.

**n8n só orquestra.** Ele agenda e chama a API. Extração, chunking, embeddings, retrieval e
cálculo de métricas ficam no backend. Desligar o n8n não quebra nenhuma funcionalidade.

## Avaliação de qualidade

O projeto trata retrieval como algo mensurável, não como caixa-preta. Um conjunto versionado
de perguntas com os trechos que deveriam ser recuperados alimenta uma execução que calcula:

- **hit rate** — proporção de perguntas que recuperaram ao menos um trecho esperado
- **posição do primeiro acerto** — em que colocação o trecho correto apareceu
- **MRR** — média de `1 / posição`, penalizando acertos que aparecem no fim da lista

Isso permite alterar um prompt ou a estratégia de chunking e comparar objetivamente se
melhorou ou regrediu.

## Documentação

| Arquivo                                  | Conteúdo                                |
| ---------------------------------------- | --------------------------------------- |
| [CLAUDE.md](CLAUDE.md)                   | regras permanentes do projeto           |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | arquitetura atual                   |
| [docs/BUSINESS_RULES.md](docs/BUSINESS_RULES.md) | regras de negócio numeradas     |
| [docs/DATABASE.md](docs/DATABASE.md)     | modelo de dados                         |
| [docs/ROADMAP.md](docs/ROADMAP.md)       | fases e status                          |
| [normaai-n8n/DOC.md](normaai-n8n/DOC.md) | workflows de automação                  |

## Status

Em construção, por fases. O estado atual de cada uma está em
[docs/ROADMAP.md](docs/ROADMAP.md).
