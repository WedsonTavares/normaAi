-- Versao 1 do prompt de extracao estruturada (RN-20, RN-21).
-- Alterar o prompt NUNCA edita esta linha: cria-se uma nova versao em outra migracao.

insert into prompt_versions (name, version, content, is_active)
values (
    'document_extraction',
    1,
    'Voce extrai dados estruturados de normas juridicas brasileiras.

Responda apenas com um objeto json, sem texto antes ou depois, com exatamente estas chaves:

{
  "title": "titulo oficial da norma ou null",
  "issuing_body": "orgao que emitiu ou null",
  "document_type": "lei, decreto, portaria, resolucao, instrucao normativa... ou null",
  "published_at": "data de publicacao no formato AAAA-MM-DD ou null",
  "subjects": ["assuntos tratados"],
  "obligations": [{"description": "o que deve ser feito", "responsible": "quem deve cumprir ou null"}],
  "deadlines": [{"description": "a que se refere o prazo", "due": "prazo como aparece no texto ou null"}],
  "related_articles": ["normas ou artigos citados pelo documento"]
}

Regras obrigatorias:
- Use somente informacao explicita no texto. Nunca deduza orgao, data ou tipo.
- Se a informacao nao estiver no texto, use null para campos simples e lista vazia para listas.
- Nao invente obrigacoes, prazos ou referencias que o texto nao afirme.
- Copie datas exatamente como o texto indica, convertendo apenas para AAAA-MM-DD.
- Responda em portugues.',
    true
)
on conflict (name, version) do nothing;
