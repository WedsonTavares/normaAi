# NormaAI — Workflows n8n locais

Este diretório contém workflows auxiliares do NormaAI.

A regra arquitetural é simples:

**Python/FastAPI executa a lógica do produto. n8n orquestra, agenda e monitora.**

O n8n não deve implementar o núcleo da RAG, chunking, embeddings ou regras principais de negócio.

## Estrutura

```text
normaai-n8n/
├── README.md
├── DOC.md
├── .env.n8n.example
└── workflows/
    ├── 01-document-processing.json
    ├── 02-rag-evaluation.json
    ├── 03-api-health-monitor.json
    └── 04-error-handler.json
```

## Pré-requisitos

1. n8n local funcionando.
2. Backend FastAPI do NormaAI funcionando.
3. Variável `NORMAAI_API_URL` disponível para o processo/container do n8n.
4. Acesso a variáveis de ambiente liberado nas expressões (`N8N_BLOCK_ENV_ACCESS_IN_NODE=false`). Sem isso, `$env.NORMAAI_API_URL` volta vazio e todos os nodes HTTP falham com URL inválida.
5. Os endpoints descritos em **Contratos esperados do backend** implementados conforme cada workflow for ativado.

Veja `.env.n8n.example` para o conjunto completo de variáveis.

### URL local

Se n8n e FastAPI estiverem no mesmo Docker Compose:

```env
NORMAAI_API_URL=http://backend:8000
```

Se ambos estiverem executando diretamente na máquina, fora de containers:

```env
NORMAAI_API_URL=http://127.0.0.1:8000
```

Se n8n estiver em Docker e FastAPI estiver diretamente no host, configure a rede do Docker adequadamente e use um hostname acessível pelo container. Em Linux, prefira colocar ambos no mesmo Compose para evitar configuração específica do host.

## Importação

No n8n:

1. Abra **Workflows**.
2. Escolha **Import from File**.
3. Importe os quatro JSONs da pasta `workflows/`.
4. Não ative todos imediatamente.
5. Configure primeiro `NORMAAI_API_URL`.
6. Teste manualmente os workflows 02 e 03.
7. Teste o workflow 01 usando a Test URL do Webhook.
8. Importe e publique o workflow 04.
9. Configure o workflow 04 como **Error Workflow** dos workflows 01, 02 e 03.
10. Só então publique/ative os workflows com Schedule/Webhook.

> O n8n pode atualizar automaticamente a versão interna de alguns nodes durante a importação. Depois de importar, abra cada workflow, confira os nodes e salve uma vez.

---

# Workflow 01 — Orquestrar processamento de documento

Arquivo:

```text
01-document-processing.json
```

## Para que serve

Recebe um `document_id` por webhook e solicita ao FastAPI que processe aquele documento.

O fluxo real continua no backend:

```text
n8n
↓
FastAPI
↓
PDF
↓
extração
↓
structured extraction
↓
chunking
↓
embeddings
↓
pgvector
```

O n8n não executa essas etapas internamente.

## Entrada esperada

```json
{
  "document_id": "uuid-do-documento",
  "requested_by": "frontend"
}
```

`requested_by` é opcional.

## Nós

### 1. Receber documento

Tipo: **Webhook**

Método:

```text
POST
```

Path:

```text
normaai/document/process
```

Responsabilidade:

Receber a solicitação de processamento.

Durante desenvolvimento, utilize a **Test URL**.

Depois de publicar o workflow, utilize a **Production URL**.

### 2. Normalizar entrada

Tipo: **Edit Fields (Set)**

Responsabilidade:

Transformar diferentes formatos de entrada em um contrato simples:

```json
{
  "document_id": "...",
  "requested_by": "..."
}
```

Isso evita espalhar expressões complexas por vários nodes.

### 3. Validar document_id

Tipo: **Code**

Responsabilidade:

Garantir que `document_id` esteja presente antes de chamar o backend.

Se não existir, o workflow falha imediatamente com:

```text
document_id é obrigatório
```

Essa falha pode ser capturada pelo Error Handler.

### 4. Processar no FastAPI

Tipo: **HTTP Request**

Executa:

```text
POST /api/documents/{document_id}/process
```

Responsabilidade:

Pedir ao backend que processe o documento.

Este node **não possui retry**.

Processar um documento não é uma operação segura de repetir às cegas: uma segunda chamada
poderia duplicar chunks, embeddings e custo de OpenAI. O backend protege isso pela RN-08
(pedido em documento já `processing` devolve o status atual sem iniciar novo processamento),
mas o workflow não depende dessa proteção para estar correto.

Se a chamada falhar, o erro vai para o Error Handler e o reprocessamento é decidido por um humano.

O backend continua sendo responsável por:

extração do PDF  
extração estruturada  
chunking  
embeddings  
persistência  
status do documento  

### 5. Responder sucesso

Tipo: **Respond to Webhook**

Responsabilidade:

Retornar para quem chamou o webhook a resposta gerada pelo backend.

## Como testar

Com o workflow em modo de teste, copie a Test URL e execute:

```bash
curl -X POST "URL_DE_TESTE_DO_N8N" \
  -H "Content-Type: application/json" \
  -d '{"document_id":"UUID_REAL_DO_DOCUMENTO"}'
```

---

# Workflow 02 — Avaliação automática da RAG

Arquivo:

```text
02-rag-evaluation.json
```

## Para que serve

Executa periodicamente a suíte de avaliação da RAG.

A lógica das métricas continua no Python.

O n8n apenas agenda a execução e recebe o resultado.

## Fluxo

```text
Schedule ou Manual Trigger
↓
Preparar execução
↓
FastAPI /api/evaluations/run
↓
Resumir métricas
```

## Nós

### 1. Executar manualmente

Tipo: **Manual Trigger**

Responsabilidade:

Permitir executar a avaliação durante desenvolvimento sem esperar o agendamento.

É o primeiro node que deve ser utilizado enquanto a feature está sendo criada.

### 2. Executar diariamente

Tipo: **Schedule Trigger**

Responsabilidade:

Rodar a suíte automaticamente a cada 24 horas.

Para portfólio/local, uma execução diária é suficiente.

Não há benefício em executar avaliações pesadas a cada poucos minutos.

### 3. Preparar execução

Tipo: **Edit Fields (Set)**

Cria:

```text
triggered_at
```

Responsabilidade:

Registrar quando o n8n iniciou a avaliação.

### 4. Executar avaliação no FastAPI

Tipo: **HTTP Request**

Executa:

```text
POST /api/evaluations/run
```

Exemplo de body:

```json
{
  "source": "n8n",
  "triggered_at": "..."
}
```

O Python deve:

carregar dataset de avaliação  
executar perguntas  
realizar retrieval  
calcular métricas  
persistir resultado  
retornar resumo  

Este node **não possui retry**. Cada execução gera um `run_id` novo e roda a suíte inteira
contra a OpenAI — repetir automaticamente duplicaria custo e poluiria o histórico de métricas.
Falha vai para o Error Handler e é reexecutada por decisão humana (RN-92).

### 5. Resumir métricas

Tipo: **Code**

Responsabilidade:

Reduzir a resposta do backend para os campos mais importantes.

Exemplo:

```json
{
  "status": "evaluation_completed",
  "run_id": "...",
  "questions": 20,
  "hit_rate": 0.95,
  "mrr": 0.89
}
```

A resposta original continua disponível no campo `raw`.

## Por que este workflow é importante

Ele mostra que o NormaAI não trata a IA como uma caixa-preta.

O produto possui um ciclo mensurável:

```text
alterar prompt/retrieval
↓
executar avaliação
↓
comparar métricas
↓
validar regressão ou melhoria
```

---

# Workflow 03 — Monitoramento local da API

Arquivo:

```text
03-api-health-monitor.json
```

## Para que serve

Verificar periodicamente se o FastAPI continua acessível.

Não é uma solução completa de observabilidade.

É um watchdog simples e adequado ao escopo do projeto.

## Fluxo

```text
Schedule ou Manual Trigger
↓
GET /health
↓
validar resposta
```

## Nós

### 1. Testar manualmente

Tipo: **Manual Trigger**

Responsabilidade:

Validar a integração durante desenvolvimento.

### 2. Verificar a cada 5 minutos

Tipo: **Schedule Trigger**

Responsabilidade:

Executar o health check periodicamente.

Cinco minutos é suficiente para um projeto de portfólio local.

### 3. Consultar health

Tipo: **HTTP Request**

Executa:

```text
GET /health
```

Possui retry simples.

Se o backend estiver indisponível e as tentativas falharem, o workflow falha.

Essa falha deve ser encaminhada ao Error Handler.

### 4. Validar saúde

Tipo: **Code**

Aceita os status:

```text
ok
healthy
up
```

Caso o backend retorne outro status, o node gera um erro.

Resposta sem o campo `status` também é tratada como falha. Um monitor que interpreta ausência
de informação como "saudável" não serve para nada.

Exemplo de endpoint:

```json
{
  "status": "ok"
}
```

---

# Workflow 04 — Error Handler

Arquivo:

```text
04-error-handler.json
```

## Para que serve

Centralizar falhas ocorridas nos outros workflows.

Ele não substitui logs do FastAPI.

Ele registra erros da camada de automação.

## Configuração obrigatória

Depois de importar o Error Handler:

1. Salve/publique o workflow.
2. Abra o workflow 01.
3. Entre nas configurações do workflow.
4. Escolha `NormaAI 04 - Error Handler` como Error Workflow.
5. Repita para 02 e 03.

## Nós

### 1. Erro em workflow

Tipo: **Error Trigger**

Responsabilidade:

Receber os dados de uma execução que falhou em outro workflow configurado para utilizar este Error Workflow.

Pode receber informações como:

workflow  
execution  
erro  
último node executado  

### 2. Normalizar erro

Tipo: **Code**

Transforma o payload do n8n em um formato previsível:

```json
{
  "source": "n8n",
  "workflow_id": "...",
  "workflow_name": "...",
  "execution_id": "...",
  "execution_url": "...",
  "last_node_executed": "...",
  "error_message": "...",
  "error_stack": "...",
  "recorded_at": "..."
}
```

Isso simplifica debug e persistência.

### 3. Registrar erro no FastAPI

Tipo: **HTTP Request**

Executa:

```text
POST /api/operations/n8n-errors
```

Responsabilidade:

Entregar o erro ao backend para registro.

O node está configurado para não derrubar o Error Handler caso o próprio endpoint de registro esteja indisponível.

Para o MVP, o backend pode apenas registrar esse payload em log estruturado.

Não é obrigatório criar uma tabela somente para isso.

---

# Contratos esperados do backend

Os workflows assumem estes endpoints.

Convenção do projeto: rotas de recurso usam o prefixo `/api`; `GET /health` fica na raiz para
que o monitoramento não dependa do prefixo. Ver `docs/ARCHITECTURE.md`.

## Health

```http
GET /health
```

Resposta mínima:

```json
{
  "status": "ok"
}
```

## Processar documento

```http
POST /api/documents/{document_id}/process
```

Resposta sugerida:

```json
{
  "document_id": "...",
  "status": "processed"
}
```

Ou, caso o backend use processamento assíncrono:

```json
{
  "document_id": "...",
  "status": "processing"
}
```

## Executar avaliação

```http
POST /api/evaluations/run
```

Body:

```json
{
  "source": "n8n",
  "triggered_at": "..."
}
```

Resposta:

```json
{
  "run_id": "...",
  "questions": 20,
  "hit_rate": 0.95,
  "mrr": 0.89
}
```

As métricas estão definidas na RN-72 do `docs/BUSINESS_RULES.md`. O `run_id` agrupa as linhas
daquela execução na tabela `evaluations`.

## Registrar erro do n8n

```http
POST /api/operations/n8n-errors
```

Body:

```json
{
  "source": "n8n",
  "workflow_id": "...",
  "workflow_name": "...",
  "execution_id": "...",
  "last_node_executed": "...",
  "error_message": "...",
  "recorded_at": "..."
}
```

Este endpoint é auxiliar.

Ele não precisa criar nova arquitetura ou subsistema. Responde 202 e apenas registra em log
estruturado (RN-91): erro de automação não é dado de negócio e não vira tabela.

---

# O que NÃO deve ser colocado no n8n

Não mova para o n8n:

extração principal de PDF  
chunking  
geração de embeddings  
similarity search  
retrieval  
montagem do contexto RAG  
avaliação matemática  
regras de negócio principais  

Essas responsabilidades permanecem no FastAPI.

## Regra

```text
n8n decide QUANDO executar.
FastAPI sabe COMO executar.
```

---

# Ordem recomendada de desenvolvimento

## Etapa 1

Implemente:

```text
GET /health
```

Importe e teste o workflow 03.

## Etapa 2

Implemente:

```text
POST /api/documents/{document_id}/process
```

Importe e teste o workflow 01.

## Etapa 3

Depois que a RAG funcionar em Python, implemente:

```text
POST /api/evaluations/run
```

Teste o workflow 02 manualmente.

Só depois ative o Schedule Trigger.

## Etapa 4

Implemente o Error Handler.

O endpoint `/api/operations/n8n-errors` pode inicialmente apenas gerar log estruturado.

---

# Debug

Quando ocorrer falha:

1. Abra **Executions** no n8n.
2. Veja qual node ficou vermelho.
3. Inspecione INPUT e OUTPUT do node.
4. Confira `document_id`, URL chamada e resposta HTTP.
5. Se o problema estiver no FastAPI, continue o diagnóstico nos logs do backend.
6. Não coloque lógica extra no n8n para esconder um bug do backend.

## Exemplo

```text
Processar no FastAPI
HTTP 500
```

O problema provavelmente está no backend.

```text
Validar document_id
document_id é obrigatório
```

O problema está no payload que chamou o webhook.

```text
Consultar health
Connection refused
```

O backend está desligado, URL está incorreta ou n8n não consegue alcançar o host.

---

# Produção futura

Estes workflows foram desenhados para desenvolvimento local e portfólio.

Antes de expor webhooks publicamente:

adicione autenticação  
restrinja origem quando aplicável  
não exponha tokens no workflow  
utilize credenciais/variáveis de ambiente  
revise políticas de retry  
configure URL pública corretamente  

Não adicione essa complexidade antes de existir necessidade.
