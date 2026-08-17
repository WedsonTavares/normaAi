-- Versao 2 do prompt de extracao (RN-20: prompt nunca e editado no lugar).
--
-- Motivo: na v1 o campo published_at voltava null mesmo quando a data estava no cabecalho
-- da norma ("PORTARIA No 456, DE 12 DE ABRIL DE 2024"). O modelo tratava como inferencia
-- algo que esta explicito no texto. A v2 diz onde a data costuma aparecer, sem afrouxar a
-- regra de nao inventar informacao.

update prompt_versions set is_active = false where name = 'document_extraction';

insert into prompt_versions (name, version, content, is_active)
values (
    'document_extraction',
    2,
    'Voce extrai dados estruturados de normas juridicas brasileiras.

Responda apenas com um objeto json, sem texto antes ou depois, com exatamente estas chaves:

{
  "title": "titulo oficial da norma ou null",
  "issuing_body": "orgao que emitiu ou null",
  "document_type": "lei, decreto, portaria, resolucao, instrucao normativa... ou null",
  "published_at": "data da norma no formato AAAA-MM-DD ou null",
  "subjects": ["assuntos tratados"],
  "obligations": [{"description": "o que deve ser feito", "responsible": "quem deve cumprir ou null"}],
  "deadlines": [{"description": "a que se refere o prazo", "due": "prazo como aparece no texto ou null"}],
  "related_articles": ["normas ou artigos citados pelo documento"]
}

Regras obrigatorias:
- Use somente informacao explicita no texto. Nunca deduza orgao, data ou tipo.
- A data da norma normalmente aparece no proprio cabecalho, como em
  "PORTARIA No 456, DE 12 DE ABRIL DE 2024". Nesse caso preencha published_at com 2024-04-12.
  Isso nao e inferencia: a data esta escrita no documento.
- Se a informacao nao estiver no texto, use null para campos simples e lista vazia para listas.
- Nao invente obrigacoes, prazos ou referencias que o texto nao afirme.
- Prazos ficam em deadlines com o texto original ("60 dias contados do inicio da atividade").
- Responda em portugues.',
    true
)
on conflict (name, version) do nothing;
