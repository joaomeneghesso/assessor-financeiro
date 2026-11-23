---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 68
tags: [modulo, telegram-telas-e-conversa]
---
# efeito_baixa.py

> Efeito de um registro no dinheiro: saldo da conta e sobra prevista, antes → depois.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 68 · **Funções:** 4 · **Classes:** 0

## Usa

- [[consulta_cache.py]]
- [[database.py]]
- [[faturas_competencia.py]]
- [[saldo_resumo.py]]
- [[services.py]]

## Usado por

- [[telegram_experiencia.py]] — `confirmacao`, `instantaneo`, `previa`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `confirmacao` | 53 | 1 | 0 | Bloco para a tela "Registro salvo": saldo da conta e sobra prevista, antes → depois. |
| `instantaneo` | 26 | 1 | 0 | Saldo da conta do registro e sobra prevista no mês do registro (ou None). |
| `previa` | 42 | 1 | 0 | Linha para a prévia: o que vai acontecer com o saldo da conta ao salvar. |

## Tudo que define

- `_norm` (L22, 2 linhas)
- `instantaneo` (L26, 14 linhas) — Saldo da conta do registro e sobra prevista no mês do registro (ou None).
- `previa` (L42, 9 linhas) — Linha para a prévia: o que vai acontecer com o saldo da conta ao salvar.
- `confirmacao` (L53, 16 linhas) — Bloco para a tela "Registro salvo": saldo da conta e sobra prevista, antes → depois.

## Testes que usam (1)

- `tests/test_efeito_baixa.py`

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
