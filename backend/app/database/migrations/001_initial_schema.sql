-- Schema inicial do NormaAI. Ver docs/DATABASE.md.

create extension if not exists vector;
create extension if not exists pgcrypto;

-- Um PDF enviado e seu estado de processamento.
create table if not exists documents (
    id            uuid primary key default gen_random_uuid(),
    filename      text not null,
    storage_path  text not null,
    content_hash  text not null unique,
    page_count    integer,
    page_texts    jsonb,
    status        text not null default 'pending'
                  check (status in ('pending', 'processing', 'ready', 'failed')),
    error_message text,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);

create index if not exists documents_status_idx on documents (status);
create index if not exists documents_created_at_idx on documents (created_at desc);

-- Versionamento dos prompts de extracao.
create table if not exists prompt_versions (
    id         uuid primary key default gen_random_uuid(),
    name       text not null,
    version    integer not null,
    content    text not null,
    is_active  boolean not null default false,
    created_at timestamptz not null default now(),
    unique (name, version)
);

-- No maximo uma versao ativa por nome.
create unique index if not exists prompt_versions_active_idx
    on prompt_versions (name) where is_active;

-- Trechos indexados e seus vetores.
create table if not exists document_chunks (
    id            uuid primary key default gen_random_uuid(),
    document_id   uuid not null references documents (id) on delete cascade,
    chunk_index   integer not null,
    content       text not null,
    page_start    integer not null,
    page_end      integer not null,
    article_label text,
    char_count    integer not null,
    embedding     vector(1536),
    created_at    timestamptz not null default now(),
    unique (document_id, chunk_index)
);

create index if not exists document_chunks_document_idx on document_chunks (document_id);
create index if not exists document_chunks_embedding_idx
    on document_chunks using hnsw (embedding vector_cosine_ops);

-- Resultado da extracao estruturada. Historico preservado.
create table if not exists document_extractions (
    id                uuid primary key default gen_random_uuid(),
    document_id       uuid not null references documents (id) on delete cascade,
    prompt_version_id uuid not null references prompt_versions (id),
    model             text not null,
    data              jsonb not null,
    created_at        timestamptz not null default now()
);

create index if not exists document_extractions_document_idx
    on document_extractions (document_id, created_at desc);

-- Uma linha por pergunta avaliada. run_id agrupa a execucao.
create table if not exists evaluations (
    id                  uuid primary key default gen_random_uuid(),
    run_id              uuid not null,
    question            text not null,
    expected_reference  text,
    document_id         uuid references documents (id) on delete set null,
    answer              text,
    retrieved_chunk_ids uuid[] not null default '{}',
    hit                 boolean,
    hit_position        integer,
    human_rating        text check (human_rating in ('good', 'partial', 'bad')),
    notes               text,
    created_at          timestamptz not null default now()
);

create index if not exists evaluations_run_idx on evaluations (run_id);
create index if not exists evaluations_created_at_idx on evaluations (created_at desc);
