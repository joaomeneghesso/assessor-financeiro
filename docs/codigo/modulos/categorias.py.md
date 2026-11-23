---
tipo: modulo
grupo: Núcleo financeiro
linhas: 148
tags: [modulo, nucleo-financeiro]
---
# categorias.py

> Taxonomia e categorização canônica compartilhada pelo assessor.

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 148 · **Funções:** 5 · **Classes:** 0

## Usa

- [[categorias_pessoais.py]] *(importação tardia, dentro de função)*

## Usado por

- [[busca_lancamentos.py]] — `canonicalizar_categoria`
- [[compromissos.py]] — `inferir_categoria`
- [[database.py]] — `canonicalizar_categoria`
- [[fixos_edicao.py]] — `canonicalizar_categoria`
- [[parser_financeiro.py]] — `canonicalizar_categoria`, `inferir_categoria`
- [[registro_conversa.py]] — `canonicalizar_categoria`
- [[services.py]] — `canonicalizar_categoria`, `sugerir_categoria`
- [[sugestoes_lancamento.py]] — `canonicalizar_categoria`
- [[telegram_experiencia.py]] — `categoria_permitida_ia`, `sugerir_categoria`
- [[telegram_registros.py]] — `canonicalizar_categoria`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `canonicalizar_categoria` | 107 | 8 | 1 | Normaliza categorias conhecidas sem destruir uma escolha personalizada. |
| `sugerir_categoria` | 115 | 2 | 2 | Sugere uma categoria canônica ou ``None`` sem evidência suficiente. |
| `inferir_categoria` | 140 | 2 | 1 |  |
| `categoria_permitida_ia` | 144 | 1 | 0 | Aceita da IA somente nomes pertencentes à taxonomia conhecida. |

## Tudo que define

- `_chave_categoria` (L19, 4 linhas)
- `canonicalizar_categoria` (L107, 6 linhas) — Normaliza categorias conhecidas sem destruir uma escolha personalizada.
- `sugerir_categoria` (L115, 23 linhas) — Sugere uma categoria canônica ou ``None`` sem evidência suficiente.
- `inferir_categoria` (L140, 2 linhas)
- `categoria_permitida_ia` (L144, 4 linhas) — Aceita da IA somente nomes pertencentes à taxonomia conhecida.

## Testes que usam (2)

- `tests/test_categorizacao_unificada.py`
- `tests/test_confiabilidade_413.py`

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
