Você atuará como Arquiteto de Software e Engenheiro Sênior responsável pelo projeto NormaAI.

Sua função inicial NÃO é sair codificando.

Primeiro analise o objetivo do projeto, defina a arquitetura mínima necessária e crie os documentos que servirão como fonte de verdade durante todo o desenvolvimento.

## Objetivo do produto

NormaAI é uma aplicação para leitura, estruturação, indexação, pesquisa e análise de documentos legais e normativos utilizando IA.

Fluxo principal:

Upload de PDF
→ extração do texto
→ extração estruturada de informações
→ divisão em chunks
→ geração de embeddings
→ armazenamento vetorial
→ busca semântica
→ RAG
→ resposta com referência ao trecho original
→ avaliação da qualidade

O projeto será utilizado como projeto técnico de portfólio, portanto deve demonstrar boas práticas reais de engenharia sem overengineering.

## Stack obrigatória

Utilize sempre versões estáveis atuais no momento da instalação.

Frontend:
React
TypeScript
Vite
Tailwind CSS

Backend:
Python
FastAPI
Pydantic

Banco:
Supabase
PostgreSQL
pgvector

IA:
OpenAI API
Embeddings
Structured Outputs
RAG

RAG:
LlamaIndex apenas onde realmente agregar valor.

Testes:
Pytest no backend
Testes essenciais no frontend quando necessário

Infra:
Docker apenas onde facilitar execução e deploy
Variáveis de ambiente
Git/GitHub

## Estrutura

Use:

frontend/
backend/
docs/

Frontend:

frontend/src/
components/
pages/
services/
hooks/
types/
lib/

Backend:

backend/app/
api/
services/
schemas/
core/
database/
tests/

Não crie camadas, interfaces, factories, repositories ou abstrações sem necessidade concreta.

## Princípios obrigatórios

Prioridade máxima para:

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

Código deve ser escrito para humanos antes de ser escrito para frameworks.

Evite:

microserviços
DDD exagerado
Clean Architecture aplicada de maneira artificial
event sourcing
CQRS
abstrações prematuras
classes sem necessidade
helpers genéricos desnecessários
arquivos gigantes
dependências que resolvam problemas triviais
duplicação de lógica
comentários explicando código confuso

Prefira código simples a código inteligente.

## Regras arquiteturais

Frontend nunca acessa diretamente APIs da OpenAI.

Toda comunicação com IA passa pelo backend.

Credenciais nunca podem chegar ao navegador.

Rotas HTTP devem ser pequenas.

Regras de negócio ficam nos services.

Schemas Pydantic definem entrada e saída da API.

Toda integração externa deve possuir tratamento de erro claro.

Logs devem permitir identificar onde ocorreu uma falha.

Erros apresentados ao usuário não devem expor stack traces ou credenciais.

Toda configuração sensível deve vir de variáveis de ambiente.

## Banco inicial

Planeje somente as tabelas necessárias para:

documents
document_chunks
document_extractions
prompt_versions
evaluations

Só crie tabelas adicionais quando existir necessidade real.

## Escopo do MVP

O MVP deve possuir:

1. Upload de PDF

2. Listagem de documentos

3. Processamento e extração de texto

4. Extração estruturada com IA:
   título
   órgão
   tipo
   data
   assuntos
   obrigações
   prazos
   artigos relacionados

5. Chunking

6. Embeddings

7. Armazenamento usando pgvector

8. Busca semântica

9. Perguntas via RAG

10. Respostas citando artigo, página ou trecho original sempre que possível

11. Versionamento simples dos prompts de extração

12. Tela de avaliação

13. Conjunto pequeno de perguntas esperadas para medir qualidade do retrieval

## Fora do MVP

Não implementar inicialmente:

login complexo
multi tenancy
pagamentos
assinaturas
painel administrativo
microserviços
OCR avançado
filas distribuídas
Kafka
Redis
Kubernetes
observabilidade complexa

Esses itens só entram se aparecer uma necessidade concreta.

## Documentação obrigatória

Antes de implementar funcionalidades, crie:

docs/ARCHITECTURE.md
docs/BUSINESS_RULES.md
docs/ROADMAP.md
docs/DATABASE.md

Também crie ou atualize CLAUDE.md na raiz.

CLAUDE.md deve resumir as regras permanentes que todo desenvolvedor ou agente de IA deverá seguir.

## Roadmap esperado

Organize o desenvolvimento aproximadamente em:

Fase 1
estrutura do projeto e configuração

Fase 2
upload e processamento de documentos

Fase 3
extração estruturada

Fase 4
banco, chunks e embeddings

Fase 5
busca semântica e RAG

Fase 6
frontend completo

Fase 7
avaliação e métricas

Fase 8
testes, revisão e documentação

Cada fase deve gerar algo funcional antes de avançar.

## Regra principal

Não programe para uma necessidade futura imaginária.

Implemente a solução mais simples que resolva corretamente o requisito atual.

Antes de adicionar qualquer biblioteca ou arquitetura nova, pergunte internamente:

Existe um problema concreto que justifique isso?

Se não existir, não adicione.

Agora analise o projeto existente.

Se estiver vazio, prepare sua arquitetura.

Crie os documentos de governança mencionados.

Depois apresente resumidamente:

arquitetura escolhida
estrutura de diretórios
modelo de dados
roadmap
principais decisões técnicas
riscos encontrados

Somente depois disso considere o projeto pronto para iniciar a implementação.
