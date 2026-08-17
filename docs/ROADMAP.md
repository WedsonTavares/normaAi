# ROADMAP.md — NormaAI

Status de cada fase. Só é marcado como concluído o que foi implementado, testado e **aprovado**
na revisão. Nada parcialmente implementado é marcado como concluído.

Legenda: `⬜ não iniciada` · `🟡 em andamento` · `✅ concluída e aprovada`

---

## Fase 1 — Estrutura do projeto e configuração ✅

**Objetivo:** repositório executável de ponta a ponta, sem funcionalidade de negócio.

- [x] Estrutura de diretórios de `backend/` e `frontend/`
- [x] Backend FastAPI com `main.py`, configuração via `pydantic-settings`, logging e handlers de erro
- [x] Endpoint `GET /health` retornando status da aplicação
- [x] `requirements.txt`, `requirements-dev.txt`, `pyproject.toml` (ruff, mypy, pytest)
- [x] Frontend Vite + React + TypeScript + Tailwind, com `services/api.ts` e chamada ao `/health`
- [x] `.env.example` no backend e no frontend
- [x] `.gitignore` e repositório Git inicializado
- [x] `docker-compose.yml` com Postgres + pgvector para desenvolvimento local
- [x] Testes do backend rodando (`pytest`) cobrindo health, configuração e formato de erro
- [x] Testes do frontend (`vitest`) cobrindo o tratamento de erro de `services/api.ts`
- [x] Lint, type check e build passando nos dois lados

**Pronto quando:** backend sobe, `/health` responde, frontend sobe e exibe o status vindo do
backend, e todos os comandos de qualidade passam.

**Validado:** backend e frontend executados juntos; `/health` respondendo 200 e erros no formato
único da API; 12 testes de backend e 4 de frontend passando; ruff, mypy, tsc, oxlint e build limpos.

**Aprovada em 2026-08-17.** O workflow 03 do n8n já funciona contra este `/health`.

---

## Fase 2 — Upload e processamento de documentos 🟡 aguardando aprovação

- [x] Migração `001_initial_schema.sql` com as cinco tabelas e a extensão `vector`
- [x] Script de migração (`python -m app.database.migrate`), idempotente
- [x] `POST /api/documents` — upload de PDF com validação de tipo e tamanho (RN-01, RN-02)
- [x] Deduplicação por SHA-256 (RN-04)
- [x] Extração de texto por página com `pypdf`
- [x] Ciclo de vida do documento com `BackgroundTasks` (RN-05, RN-06)
- [x] `POST /api/documents/{id}/process` idempotente (RN-08)
- [x] `GET /api/documents` e `GET /api/documents/{id}`
- [x] `DELETE /api/documents/{id}` com remoção em cascata e do arquivo (RN-07)
- [x] `POST /api/operations/n8n-errors` registrando em log estruturado (RN-91)
- [x] Testes: validação de upload, deduplicação, extração de texto, transições de status, idempotência
- [ ] Validar workflows 01 e 04 do n8n contra o backend real

**Pronto quando:** é possível enviar um PDF, acompanhar o status e ler o texto extraído, e o
workflow 01 dispara o processamento sem duplicar trabalho ao ser repetido.

**Validado manualmente** contra PostgreSQL real: upload → `ready` com 2 páginas extraídas;
upload duplicado devolveu o mesmo documento; não-PDF → 400; inexistente → 404; UUID inválido
→ 422; `/api/operations/n8n-errors` → 202. 27 testes passando (5 de integração, pulados sem
`TEST_DATABASE_URL`).

**Correção durante a fase:** `connection()` capturava `Exception` genérica e convertia
qualquer erro em `ExternalServiceError`. Um upload inválido devolvia 502 em vez de 400, e um
documento inexistente devolveria 502 em vez de 404. Passou a capturar apenas erros do psycopg.

---

## Fase 3 — Extração estruturada 🟡 aguardando aprovação

- [x] Schemas Pydantic dos campos extraídos (RN-10)
- [x] Seed do prompt inicial em `prompt_versions` (RN-20, RN-21)
- [x] `extraction_service` com validação obrigatória da saída (RN-12)
- [x] Persistência em `document_extractions` com modelo e versão do prompt (RN-13, RN-14)
- [x] `GET /api/documents/{id}/extraction`
- [x] Tratamento de erro e timeout do provedor de IA (RN-81)
- [x] Testes com dublê: saída válida, JSON inválido, resposta vazia, fora do schema, timeout

**Pronto quando:** um documento processado exibe seus dados estruturados validados.

**Validado com a API real** sobre uma portaria de exemplo: título, órgão, tipo, 2 assuntos,
2 obrigações com responsável, 2 prazos e 2 normas relacionadas — pipeline completo em ~48s.

**Iteração de prompt medida (RN-20):** a v1 devolvia `published_at: null` mesmo com a data no
cabeçalho, por tratá-la como inferência. A v2 explicita onde a data aparece, sem afrouxar a
regra de não inventar. Resultado: `2024-04-12`. As duas extrações seguem no banco (RN-14).

**Correção durante a fase:** `storage.read_pdf` estourava `FileNotFoundError` quando o
registro existia mas o arquivo sumira do disco, e o usuário via "falha inesperada". Agora
devolve mensagem explicando que o PDF precisa ser reenviado.

---

## Fase 4 — Banco, chunks e embeddings ⬜

- [ ] Chunking por artigo com fallback por janela e sobreposição (RN-30, RN-31, RN-32)
- [ ] Geração de embeddings em lote (RN-40, RN-41)
- [ ] Persistência dos chunks com metadados e vetores
- [ ] Índice HNSW sobre `embedding`
- [ ] Integração do chunking + embeddings ao pipeline de processamento
- [ ] Testes de chunking (com e sem artigos, limites de tamanho) e do fluxo de embeddings

**Pronto quando:** um documento `ready` possui chunks com página, artigo e vetor no banco.

---

## Fase 5 — Busca semântica e RAG ⬜

- [ ] `POST /api/search` — busca por similaridade com `top_k` e filtro por documento (RN-50 a RN-53)
- [ ] `POST /api/ask` — RAG com contexto numerado e citações (RN-60 a RN-63)
- [ ] Limiar mínimo de similaridade e resposta explícita de "sem base nos documentos" (RN-61)
- [ ] Testes: montagem de contexto, resposta sem contexto, fontes derivadas apenas dos chunks recuperados

**Pronto quando:** uma pergunta retorna resposta fundamentada com trechos verificáveis.

---

## Fase 6 — Frontend completo ⬜

- [ ] Página Documentos: upload, lista, status, exclusão
- [ ] Página Detalhe: dados estruturados, texto e chunks
- [ ] Página Busca: consulta e resultados com trecho e origem
- [ ] Página Perguntas: pergunta, resposta e fontes exibidas lado a lado
- [ ] Estados de carregando, erro e vazio em todas as telas
- [ ] Responsividade e acessibilidade básica

**Pronto quando:** o fluxo completo é utilizável pela interface, sem uso de API por fora.

---

## Fase 7 — Avaliação e métricas ⬜

- [ ] Conjunto de perguntas esperadas versionado no repositório (RN-70)
- [ ] `POST /api/evaluations/run` devolvendo `run_id`, `questions`, `hit_rate` e `mrr` (RN-71)
- [ ] Cálculo de hit rate, posição do primeiro acerto e MRR (RN-72)
- [ ] `GET /api/evaluations` e classificação humana (RN-73)
- [ ] Tela de avaliação com resultados e métricas
- [ ] Testes das métricas
- [ ] Validar workflow 02 do n8n manualmente antes de ativar o Schedule

**Pronto quando:** é possível medir objetivamente a qualidade do retrieval.

---

## Fase 8 — Testes, revisão e documentação ⬜

- [ ] Revisão de cobertura das partes críticas
- [ ] Revisão de segurança: credenciais, mensagens de erro, CORS, limites de upload
- [ ] `README.md` com instalação, configuração e execução
- [ ] Documentos de governança revisados e consistentes com o código
- [ ] Limpeza de código morto

**Pronto quando:** um terceiro clona o repositório e roda o projeto seguindo apenas o README.

---

## Histórico de aprovações

| Fase | Data       | Status    |
| ---- | ---------- | --------- |
| 1    | 2026-08-17 | aprovada  |
| 2    | —          | a iniciar |
