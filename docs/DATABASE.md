# DATABASE.md — NormaAI

Modelo de dados **atual**. PostgreSQL (Supabase) com extensão `pgvector`.
Autoridade superior: `CLAUDE.md`.

---

## 1. Extensões

```sql
create extension if not exists vector;
create extension if not exists pgcrypto;  -- gen_random_uuid()
```

---

## 2. Relacionamentos

```
documents 1 ──── N document_chunks        (on delete cascade)
documents 1 ──── N document_extractions   (on delete cascade)
prompt_versions 1 ──── N document_extractions
documents 1 ──── N evaluations            (on delete set null, opcional)
```

---

## 3. Tabelas

### 3.1 `documents`

Um PDF enviado e seu estado de processamento.

| Coluna          | Tipo          | Regras                                                    |
| --------------- | ------------- | --------------------------------------------------------- |
| `id`            | `uuid`        | PK, `gen_random_uuid()`                                    |
| `filename`      | `text`        | not null — nome original enviado pelo usuário              |
| `storage_path`  | `text`        | not null — caminho do arquivo em disco                     |
| `content_hash`  | `text`        | not null, **unique** — SHA-256 do conteúdo (RN-04)         |
| `page_count`    | `integer`     | nulo até a extração de texto                               |
| `page_texts`    | `jsonb`       | texto de cada página, na ordem; nulo até a extração         |
| `status`        | `text`        | not null, check `pending\|processing\|ready\|failed` (RN-05) |
| `error_message` | `text`        | preenchido apenas quando `status = 'failed'`               |
| `created_at`    | `timestamptz` | not null, default `now()`                                  |
| `updated_at`    | `timestamptz` | not null, default `now()`                                  |

Índices: `unique(content_hash)`, `index(status)`, `index(created_at desc)`.

### 3.2 `document_chunks`

Trechos indexados e seus vetores.

| Coluna          | Tipo           | Regras                                                     |
| --------------- | -------------- | ---------------------------------------------------------- |
| `id`            | `uuid`         | PK                                                          |
| `document_id`   | `uuid`         | not null, FK → `documents(id)` on delete cascade            |
| `chunk_index`   | `integer`      | not null — ordem dentro do documento                        |
| `content`       | `text`         | not null                                                    |
| `page_start`    | `integer`      | not null — página inicial (1-based)                         |
| `page_end`      | `integer`      | not null — página final                                     |
| `article_label` | `text`         | ex.: `Art. 5º`; nulo quando não detectado                   |
| `char_count`    | `integer`      | not null — tamanho do trecho, útil para diagnóstico         |
| `embedding`     | `vector(1536)` | `text-embedding-3-small`; nulo apenas durante o processamento |
| `created_at`    | `timestamptz`  | not null, default `now()`                                   |

Índices:
- `unique(document_id, chunk_index)`
- `index(document_id)`
- HNSW sobre `embedding` com `vector_cosine_ops`

> A dimensão `1536` está acoplada ao modelo de embedding. Trocar o modelo exige migração
> da coluna e regeração de todos os vetores (RN-40).

### 3.3 `document_extractions`

Resultado da extração estruturada. Histórico preservado (RN-14).

| Coluna              | Tipo          | Regras                                             |
| ------------------- | ------------- | -------------------------------------------------- |
| `id`                | `uuid`        | PK                                                  |
| `document_id`       | `uuid`        | not null, FK → `documents(id)` on delete cascade    |
| `prompt_version_id` | `uuid`        | not null, FK → `prompt_versions(id)`                |
| `model`             | `text`        | not null — modelo que produziu a extração           |
| `data`              | `jsonb`       | not null — payload validado (RN-10, RN-12)          |
| `created_at`        | `timestamptz` | not null, default `now()`                           |

Índice: `index(document_id, created_at desc)` — a extração vigente é a primeira linha.

**Por que `jsonb` e não colunas:** os campos extraídos incluem listas de objetos
(obrigações, prazos) e o schema ainda pode evoluir. Normalizar agora criaria tabelas e joins
sem necessidade concreta. O contrato é garantido pelo schema Pydantic na escrita.

### 3.4 `prompt_versions`

Versionamento simples dos prompts (RN-20, RN-21).

| Coluna       | Tipo          | Regras                                          |
| ------------ | ------------- | ----------------------------------------------- |
| `id`         | `uuid`        | PK                                               |
| `name`       | `text`        | not null — ex.: `document_extraction`            |
| `version`    | `integer`     | not null — inteiro crescente por `name`          |
| `content`    | `text`        | not null — texto do prompt                       |
| `is_active`  | `boolean`     | not null, default `false`                        |
| `created_at` | `timestamptz` | not null, default `now()`                        |

Índices:
- `unique(name, version)`
- `unique(name) where is_active` — garante no máximo uma versão ativa por nome

### 3.5 `evaluations`

Resultado de cada execução de avaliação (RN-71).

| Coluna                | Tipo            | Regras                                                  |
| --------------------- | --------------- | ------------------------------------------------------- |
| `id`                  | `uuid`          | PK                                                       |
| `run_id`              | `uuid`          | not null — agrupa as linhas de uma mesma execução (RN-71) |
| `question`            | `text`          | not null                                                 |
| `expected_reference`  | `text`          | referência esperada (ex.: `Art. 12`); pode ser nula      |
| `document_id`         | `uuid`          | FK → `documents(id)` on delete set null; nulo se global  |
| `answer`              | `text`          | resposta gerada pelo RAG                                 |
| `retrieved_chunk_ids` | `uuid[]`        | not null, default `'{}'` — chunks recuperados, em ordem  |
| `hit`                 | `boolean`       | o trecho esperado foi recuperado                         |
| `hit_position`        | `integer`       | posição 1-based do primeiro acerto; nulo se não houve    |
| `human_rating`        | `text`          | check `good\|partial\|bad`; nulo até avaliação humana    |
| `notes`               | `text`          | observação livre                                         |
| `created_at`          | `timestamptz`   | not null, default `now()`                                |

Índices: `index(run_id)`, `index(created_at desc)`.

O **conjunto de perguntas esperadas** não é tabela: vive versionado no repositório em
`backend/app/services/evaluation_questions.json` (RN-70). `evaluations` guarda apenas
execuções, o que evita uma sexta tabela sem necessidade concreta.

`hit_rate` e `mrr` também não são colunas: são agregados calculados sobre as linhas de um
mesmo `run_id` (RN-72). Guardar agregado que pode ser recalculado só criaria risco de
divergência entre o total e as linhas que o originaram.

---

## 4. Migrações

Arquivos SQL numerados em `backend/app/database/migrations/`:

```
001_initial_schema.sql
002_...
```

Aplicados por `python -m app.database.migrate`, que registra o que já rodou na tabela de
controle `schema_migrations (version text primary key, applied_at timestamptz)`.

Migração é **sempre aditiva por padrão**. Alteração destrutiva exige decisão do papel de
Arquitetura e atualização deste documento.

---

## 5. Consultas centrais

**Busca por similaridade** (RN-50, RN-53):

```sql
select c.id, c.document_id, c.content, c.page_start, c.page_end, c.article_label,
       d.filename,
       1 - (c.embedding <=> %(query_embedding)s::vector) as similarity
from document_chunks c
join documents d on d.id = c.document_id
where d.status = 'ready'
  and c.embedding is not null
  and (%(document_id)s::uuid is null or c.document_id = %(document_id)s::uuid)
order by c.embedding <=> %(query_embedding)s::vector
limit %(top_k)s;
```

**Extração vigente de um documento** (RN-14):

```sql
select * from document_extractions
where document_id = %(document_id)s
order by created_at desc
limit 1;
```

**Métricas de uma execução de avaliação** (RN-72):

```sql
select count(*)                                            as questions,
       avg(case when hit then 1.0 else 0.0 end)            as hit_rate,
       avg(case when hit then 1.0 / hit_position else 0.0 end) as mrr
from evaluations
where run_id = %(run_id)s;
```
