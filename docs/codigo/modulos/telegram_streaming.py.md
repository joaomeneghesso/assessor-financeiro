---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 96
tags: [modulo, telegram-telas-e-conversa]
---
# telegram_streaming.py

> Progresso efêmero para tarefas locais demoradas, sem estado financeiro.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 96 · **Funções:** 2 · **Classes:** 1

## Usa

- [[config.py]]
- [[telegram_recursos.py]] *(importação tardia, dentro de função)*

## Usado por

- [[telegram_experiencia.py]] — `DraftProgress`
- [[telegram_midia.py]] — `DraftProgress`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `DraftProgress` | 14 | 2 | 2 | Atualiza um único sendMessageDraft; falhas apenas desativam o recurso. |

## Tudo que define

- `enabled` (L9, 3 linhas)
- classe `DraftProgress` (L14, 77 linhas) — Atualiza um único sendMessageDraft; falhas apenas desativam o recurso.
- `_seconds` (L93, 4 linhas)

## Testes que usam (2)

- `tests/test_inovacoes_410.py`
- `tests/test_performance_ia_streaming_fase4.py`

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
