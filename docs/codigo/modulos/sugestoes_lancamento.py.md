---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 167
tags: [modulo, telegram-telas-e-conversa]
---
# sugestoes_lancamento.py

> Sugestões de lançamento derivadas do histórico (somente leitura).

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 167 · **Funções:** 10 · **Classes:** 0

## Usa

- [[categorias.py]] *(importação tardia, dentro de função)*
- [[database.py]]

## Usado por

- [[telegram_experiencia.py]] — `frequentes`, `ordenar_contas`, `sugerir`, `ultimo_repetivel`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `ordenar_contas` | 108 | 1 | 1 | Mais usadas primeiro (contagem em transacoes), depois alfabética. |
| `sugerir` | 69 | 1 | 1 | Devolve {'conta','forma_pagamento','categoria','amostra'} só com o que tem evidência. |
| `frequentes` | 122 | 1 | 0 | Descrições de despesa mais usadas nos últimos ``dias`` (>= 2 usos). |
| `ultimo_repetivel` | 152 | 1 | 0 | Último lançamento (despesa ou receita) elegível para repetir: não parcelado, não fatura. |

## Tudo que define

- `_norm` (L34, 3 linhas)
- `_forma` (L39, 6 linhas)
- `_fora_do_escopo` (L47, 4 linhas)
- `_linhas` (L53, 8 linhas)
- `_elegivel` (L63, 4 linhas)
- `sugerir` (L69, 37 linhas) — Devolve {'conta','forma_pagamento','categoria','amostra'} só com o que tem evidência.
- `ordenar_contas` (L108, 12 linhas) — Mais usadas primeiro (contagem em transacoes), depois alfabética.
- `frequentes` (L122, 23 linhas) — Descrições de despesa mais usadas nos últimos ``dias`` (>= 2 usos).
- `_neg` (L147, 3 linhas)
- `ultimo_repetivel` (L152, 16 linhas) — Último lançamento (despesa ou receita) elegível para repetir: não parcelado, não fatura.

## Testes que usam (1)

- `tests/test_registro_rapido_fase2.py`

## No mapa de rotas

- **Chamadas de serviço (1):** [[fn_sugestoes_lancamento.ordenar_contas-5c6a8|sugestoes_lancamento.ordenar_contas]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
