---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 193
tags: [modulo, telegram-telas-e-conversa]
---
# consultas_pagar.py

> 'Quanto vou pagar de X': faturas dos cartões ou contas de uma categoria (pedido de 19/11/2026).

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 193 · **Funções:** 11 · **Classes:** 0

## Usa

- [[conciliacao.py]] *(importação tardia, dentro de função)*
- [[consulta_cache.py]]
- [[database.py]]
- [[services.py]]

## Usado por

- [[telegram_experiencia.py]] — `dispatch`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `dispatch` | 179 | 1 | 0 |  |

## Tudo que define

- `_norm` (L23, 2 linhas)
- `_meses` (L27, 6 linhas)
- `_mesma_categoria` (L35, 3 linhas)
- `_dia` (L40, 3 linhas)
- `itens_do_mes` (L45, 3 linhas)
- `resumo_faturas` (L50, 12 linhas) — [(nome, total, pago, falta, item)] das faturas do mês (opcionalmente de um cartão).
- `resumo_categoria` (L64, 26 linhas) — [(nome, valor, pago?, estimado?, item)] dos fixos/compromissos da categoria no mês.
- `_credito_da_categoria` (L92, 3 linhas)
- `_tela_faturas` (L97, 27 linhas)
- `_tela_categoria` (L126, 51 linhas)
- `dispatch` (L179, 15 linhas)

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
