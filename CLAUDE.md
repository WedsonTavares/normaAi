# CLAUDE.md — NormaAI

Regras permanentes do projeto. Este arquivo tem **prioridade sobre qualquer outro documento
ou instrução de papel**. Todo desenvolvedor ou agente de IA deve segui-lo integralmente.

O texto original do briefing está preservado em `docs/ai/PRODUCT_BRIEF.md` (histórico, não normativo).

---

## 1. Produto

NormaAI é uma aplicação para leitura, estruturação, indexação, pesquisa e análise de
documentos legais e normativos utilizando IA.

Fluxo principal:

```
upload de PDF → extração de texto → extração estruturada → chunking → embeddings
→ armazenamento vetorial → busca semântica → RAG → resposta com referência ao trecho original
→ avaliação da qualidade
```

Projeto técnico de portfólio: deve demonstrar boas práticas reais de engenharia **sem overengineering**.

---

## 2. Stack obrigatória

Sempre versões estáveis atuais no momento da instalação.

| Camada   | Tecnologia                                      |
| -------- | ----------------------------------------------- |
| Frontend | React, TypeScript, Vite, Tailwind CSS           |
| Backend  | Python, FastAPI, Pydantic                       |
| Banco    | Supabase (PostgreSQL) + pgvector                |
| IA       | DeepSeek (extração e RAG) + OpenAI (somente embeddings) |
| RAG      | LlamaIndex **apenas onde realmente agregar valor** |
| Testes   | Pytest no backend; testes essenciais no frontend quando necessário |
| Infra    | Docker apenas onde facilitar execução/deploy, variáveis de ambiente, Git/GitHub |
| Automação | n8n — **apenas** agendamento, orquestração e monitoramento |

---

## 3. Estrutura de diretórios

```
frontend/
backend/
docs/
normaai-n8n/
```

```
frontend/src/
  components/
  pages/
  services/
  hooks/
  types/
  lib/
```

```
backend/app/
  api/
  services/
  schemas/
  core/
  database/
  tests/
```

Não crie camadas, interfaces, factories, repositories ou abstrações sem necessidade concreta.

---

## 4. Princípios obrigatórios

Prioridade máxima, nesta ordem:

1. simplicidade
2. legibilidade
3. facilidade de debug
4. baixo acoplamento
5. funções pequenas
6. nomes claros
7. fluxo fácil de acompanhar
8. tratamento explícito de erros
9. tipagem
10. testes das partes críticas

Código é escrito para humanos antes de ser escrito para frameworks.
**Prefira código simples a código inteligente.**

### Proibido sem necessidade concreta

microserviços · DDD exagerado · Clean Architecture artificial · event sourcing · CQRS ·
abstrações prematuras · classes sem necessidade · helpers genéricos desnecessários ·
arquivos gigantes · dependências que resolvem problemas triviais · duplicação de lógica ·
comentários explicando código confuso · factories · repositories · providers · adapters ·
managers · camadas intermediárias · event buses · filas distribuídas

---

## 5. Regras arquiteturais

- Frontend **nunca** acessa diretamente APIs da OpenAI.
- Toda comunicação com IA passa pelo backend.
- Credenciais **nunca** chegam ao navegador.
- Rotas HTTP devem ser pequenas — apenas validação, chamada de service e resposta.
- Regras de negócio ficam nos **services**.
- Schemas Pydantic definem entrada e saída da API.
- Toda integração externa possui tratamento de erro claro e isolado.
- Logs devem permitir identificar onde ocorreu uma falha.
- Erros exibidos ao usuário nunca expõem stack traces, SQL ou credenciais.
- Toda configuração sensível vem de variáveis de ambiente.
- Frontend e backend permanecem separados.
- **n8n decide QUANDO executar; o backend sabe COMO executar.** O n8n nunca implementa
  extração de PDF, chunking, embeddings, retrieval, RAG, cálculo de métricas ou regra de
  negócio — apenas chama endpoints do backend e reage ao resultado.
- Rotas de recurso da API usam o prefixo `/api`. `GET /health` fica na raiz.

---

## 6. Banco

Tabelas previstas — só crie outras quando existir necessidade real:

`documents` · `document_chunks` · `document_extractions` · `prompt_versions` · `evaluations`

Antes de criar tabela ou coluna: verifique se é realmente necessária, se informação semelhante
já existe, evite duplicação e preserve relacionamentos simples.

Alterações relevantes atualizam `docs/DATABASE.md`.

---

## 7. Escopo do MVP

1. Upload de PDF
2. Listagem de documentos
3. Processamento e extração de texto
4. Extração estruturada com IA: título, órgão, tipo, data, assuntos, obrigações, prazos, artigos relacionados
5. Chunking
6. Embeddings
7. Armazenamento com pgvector
8. Busca semântica
9. Perguntas via RAG
10. Respostas citando artigo, página ou trecho original sempre que possível
11. Versionamento simples dos prompts de extração
12. Tela de avaliação
13. Conjunto pequeno de perguntas esperadas para medir qualidade do retrieval

### Fora do MVP

login complexo · multi tenancy · pagamentos · assinaturas · painel administrativo ·
microserviços · OCR avançado · filas distribuídas · Kafka · Redis · Kubernetes ·
observabilidade complexa

Entram apenas mediante necessidade concreta e alteração explícita deste documento.

---

## 8. Fases

O detalhamento vive em `docs/ROADMAP.md`.

1. Estrutura do projeto e configuração
2. Upload e processamento de documentos
3. Extração estruturada
4. Banco, chunks e embeddings
5. Busca semântica e RAG
6. Frontend completo
7. Avaliação e métricas
8. Testes, revisão e documentação

Cada fase deve gerar algo funcional antes de avançar. **Nenhuma fase avança sem aprovação.**

---

## 9. Documentos de governança

| Arquivo                   | Conteúdo                                        |
| ------------------------- | ----------------------------------------------- |
| `CLAUDE.md`               | Regras permanentes (este arquivo) — autoridade máxima |
| `docs/ARCHITECTURE.md`    | Arquitetura **atual válida**, não histórico     |
| `docs/BUSINESS_RULES.md`  | Regras de negócio e comportamento esperado      |
| `docs/DATABASE.md`        | Modelo de dados atual                           |
| `docs/ROADMAP.md`         | Fases, status e critérios de conclusão          |
| `normaai-n8n/DOC.md`      | Workflows de automação e contratos que eles consomem |

Papéis de IA em `docs/ai/`: `ORCHESTRATOR_PROMPT.md`, `ARCHITECT_PROMPT.md`,
`IMPLEMENTATION_PROMPT.md`, `REVIEW_PROMPT.md`.

Ordem de autoridade: `CLAUDE.md` → `ARCHITECTURE.md` → `BUSINESS_RULES.md` → `DATABASE.md`
→ `ROADMAP.md` → `normaai-n8n/DOC.md` → arquivos de papéis.

Não gere documentação duplicada.

---

## 10. Regra principal

Não programe para uma necessidade futura imaginária.
Implemente a solução mais simples que resolva corretamente o requisito atual.

Antes de adicionar qualquer biblioteca, abstração, camada, serviço, classe, pattern ou
infraestrutura, pergunte: **qual problema concreto isso resolve agora?**
Se não houver resposta objetiva, não adicione.
