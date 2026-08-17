# BUSINESS_RULES.md — NormaAI

Regras de negócio e comportamento esperado do sistema.
Autoridade superior: `CLAUDE.md`. Comportamento estrutural: `docs/ARCHITECTURE.md`.

---

## 1. Documentos

### RN-01 — Formato aceito
Somente arquivos PDF são aceitos no upload. Content-type e extensão são verificados.
Qualquer outro formato é rejeitado com erro 400 e mensagem clara.

### RN-02 — Tamanho máximo
Uploads acima de `MAX_UPLOAD_MB` (padrão 20 MB) são rejeitados com erro 413.

### RN-03 — Documento vazio ou ilegível
Se a extração de texto não produzir conteúdo útil (PDF apenas com imagens, corrompido ou
sem texto extraível), o documento é marcado como `failed` com mensagem explicativa.
OCR está fora do escopo do MVP.

### RN-04 — Deduplicação
O hash SHA-256 do conteúdo identifica o arquivo. Reenviar um PDF idêntico não cria um novo
documento: o sistema retorna o documento existente e informa que já havia sido enviado.

### RN-05 — Ciclo de vida
`documents.status` assume exatamente um destes valores:

| Status       | Significado                                                    |
| ------------ | -------------------------------------------------------------- |
| `pending`    | arquivo recebido e salvo, processamento ainda não iniciado      |
| `processing` | processamento em andamento                                      |
| `ready`      | texto extraído, extração estruturada, chunks e embeddings prontos |
| `failed`     | falha em alguma etapa; `error_message` explica o motivo         |

Transições válidas: `pending → processing → ready` ou `pending → processing → failed`.
Um documento `failed` pode ser reprocessado, voltando a `processing`.

### RN-06 — Falha parcial não vira sucesso
`ready` só é atribuído quando texto, extração estruturada, chunks **e** embeddings existem.
Falha em qualquer etapa resulta em `failed`, nunca em sucesso parcial silencioso.

### RN-07 — Exclusão
Excluir um documento remove em cascata seus chunks e extrações, e apaga o arquivo do disco.

### RN-08 — Processamento não concorrente
Pedir o processamento de um documento que já está `processing` **não inicia um segundo
processamento**: a API responde 200 com o status atual. Um documento `ready` só é reprocessado
mediante pedido explícito, e o reprocessamento substitui chunks e embeddings anteriores,
preservando o histórico de extrações (RN-14).

Sem essa regra, qualquer cliente que repita a chamada — o usuário clicando duas vezes ou uma
automação — duplicaria chunks, embeddings e custo de API.

---

## 2. Extração estruturada

### RN-10 — Campos extraídos
A extração produz, para cada documento:

| Campo               | Tipo             | Obrigatório | Observação                            |
| ------------------- | ---------------- | ----------- | ------------------------------------- |
| `title`             | texto            | não         | título oficial da norma               |
| `issuing_body`      | texto            | não         | órgão emissor                         |
| `document_type`     | texto            | não         | lei, decreto, portaria, resolução…    |
| `published_at`      | data (ISO 8601)  | não         | data de publicação                    |
| `subjects`          | lista de texto   | sim (pode ser vazia) | assuntos tratados            |
| `obligations`       | lista de objetos | sim (pode ser vazia) | descrição + responsável       |
| `deadlines`         | lista de objetos | sim (pode ser vazia) | descrição + prazo             |
| `related_articles`  | lista de texto   | sim (pode ser vazia) | artigos/normas referenciados  |

### RN-11 — Não inventar informação
Campos ausentes no documento retornam `null` (escalares) ou lista vazia. O modelo é instruído
a nunca inferir órgão, data ou tipo que não estejam explícitos no texto.

### RN-12 — Validação obrigatória
A saída do modelo é validada por schema Pydantic antes de ser persistida. Saída inválida é
tratada como falha da etapa de extração — nunca gravada parcialmente.

### RN-13 — Rastreabilidade
Toda extração registra qual `prompt_version` e qual modelo a produziram.

### RN-14 — Histórico de extrações
Reprocessar um documento cria uma **nova** linha em `document_extractions`. As anteriores são
preservadas. A extração vigente é a mais recente do documento.

---

## 3. Prompts

### RN-20 — Versionamento
Prompts de extração vivem em `prompt_versions`, identificados por `name` + `version` inteiro
crescente. Prompt existente **nunca** é editado no lugar: uma alteração cria nova versão.

### RN-21 — Versão ativa
Para cada `name` existe no máximo uma versão ativa. A extração sempre usa a versão ativa
no momento da execução.

---

## 4. Chunking

### RN-30 — Estratégia
O texto é dividido preferencialmente por artigo (`Art. 1º`, `Art. 2º`, …), padrão típico de
normas brasileiras. Quando não há marcação de artigos, ou quando um artigo excede o tamanho
máximo, aplica-se divisão por janela de tamanho fixo com sobreposição.

### RN-31 — Metadados do chunk
Todo chunk guarda: documento de origem, índice sequencial, página inicial, página final e,
quando detectado, o rótulo do artigo. Esses dados sustentam a citação da resposta.

### RN-32 — Chunk vazio
Chunks sem conteúdo textual relevante (apenas espaços, números de página ou cabeçalho
repetido) são descartados.

---

## 5. Embeddings

### RN-40 — Modelo único por base
Todos os embeddings de uma mesma base são gerados pelo mesmo modelo e com a mesma dimensão.
Trocar o modelo exige migração e regeração de todos os embeddings.

### RN-41 — Consistência
Um chunk sem embedding não participa da busca. Se a geração falhar, o documento é marcado
como `failed` (ver RN-06).

---

## 6. Busca semântica

### RN-50 — Similaridade
A busca usa similaridade de cosseno sobre `document_chunks.embedding`, com `top_k`
configurável (padrão 5, máximo 20).

### RN-51 — Escopo
A busca pode ser global ou restrita a um documento específico.

### RN-52 — Resultado
Cada resultado devolve: trecho, documento de origem, página, artigo quando houver, e o
score de similaridade.

### RN-53 — Documentos não prontos
Somente chunks de documentos com status `ready` participam da busca.

---

## 7. RAG

### RN-60 — Fonte da resposta
A resposta é gerada exclusivamente a partir dos chunks recuperados. O modelo é instruído a
não usar conhecimento próprio sobre legislação.

### RN-61 — Ausência de contexto
Se nenhum chunk for recuperado, ou se todos ficarem abaixo do limiar mínimo de similaridade,
o sistema responde que não encontrou base nos documentos e **não** chama o modelo de geração.

### RN-62 — Citação obrigatória
Toda resposta devolve a lista de fontes efetivamente utilizadas, com documento, página,
artigo quando houver e o trecho original.

### RN-63 — Sem citação inventada
As fontes exibidas ao usuário vêm dos chunks realmente recuperados do banco, nunca de texto
produzido pelo modelo. Referência que o modelo cite e que não exista entre os chunks
recuperados não é apresentada como fonte.

---

## 8. Avaliação

### RN-70 — Conjunto de perguntas
Existe um conjunto pequeno e versionado de perguntas esperadas, com os documentos ou trechos
que deveriam ser recuperados. Ele vive no repositório, junto do código.

### RN-71 — Execução
Executar a avaliação roda cada pergunta pelo mesmo fluxo de RAG usado em produção e registra
em `evaluations` uma linha por pergunta: pergunta, resposta gerada, chunks recuperados e as
métricas calculadas. Todas as linhas de uma mesma execução compartilham o mesmo `run_id`,
que é o identificador devolvido por quem disparou a avaliação.

### RN-72 — Métricas
Métricas do MVP, sobre o retrieval, calculadas por execução (`run_id`):

| Métrica       | Definição                                                              |
| ------------- | ---------------------------------------------------------------------- |
| `hit_rate`    | proporção de perguntas que recuperaram ao menos um trecho esperado      |
| `hit_position`| posição 1-based do primeiro acerto de cada pergunta; nulo se não houve  |
| `mrr`         | média de `1 / hit_position`; perguntas sem acerto contam como 0         |

`mrr` é derivado de `hit_position` — não é armazenado por linha, é calculado na execução.

### RN-73 — Avaliação humana
A tela de avaliação permite classificar manualmente uma resposta como `good`, `partial` ou
`bad`, com observação opcional. A classificação humana nunca é sobrescrita por execução automática.

---

## 9. Erros e segurança

### RN-80 — Mensagens ao usuário
Erros exibidos ao usuário são objetivos e nunca contêm stack trace, SQL, nome de tabela,
prompt interno ou credencial.

### RN-81 — Falha de integração externa
Falha de OpenAI ou banco é registrada em log com a causa real e devolvida ao usuário como
mensagem genérica com status apropriado (502 para dependência externa).

### RN-82 — Credenciais
Nenhuma credencial trafega para o frontend nem é gravada em log.

---

## 10. Automação

### RN-90 — Independência do n8n
O backend não depende do n8n para funcionar. Todo endpoint chamado por automação também pode
ser chamado pelo frontend ou por `curl`. Desligar o n8n não quebra nenhuma funcionalidade.

### RN-91 — Registro de falhas da automação
`POST /api/operations/n8n-errors` recebe a falha ocorrida em um workflow e a registra em log
estruturado, respondendo 202. Não cria tabela: erro de automação não é dado de negócio.

### RN-92 — Endpoints chamados por automação
Endpoints consumidos por workflow são idempotentes (RN-08) ou não têm retry configurado no
workflow. Nunca as duas coisas ausentes ao mesmo tempo.
