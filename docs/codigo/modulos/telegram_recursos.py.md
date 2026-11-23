---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 222
tags: [modulo, telegram-telas-e-conversa]
---
# telegram_recursos.py

> Recursos de leitura e aprendizado; nenhum pagamento é confirmado aqui.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 222 · **Funções:** 9 · **Classes:** 1

## Usa

- [[config.py]]
- [[database.py]]
- [[saldo_resumo.py]]
- [[services.py]]
- [[telegram_design.py]]
- [[telegram_experiencia.py]] *(importação tardia, dentro de função)*

## Usado por

- [[app.py]] — `TopicPending`, `_resume`, `deep_action`, `scope_update`, `thread_id`, `thread_options`
- [[telegram_alertas.py]] — `_resume`
- [[telegram_experiencia.py]] — `_resume`, `dispatch`, `protect_financial_content`, `rich_summary`, `send_rich`, `thread_id`, `thread_options`
- [[telegram_streaming.py]] — `thread_id`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `_resume` | 179 | 3 | 0 |  |
| `thread_id` | 184 | 3 | 0 |  |
| `thread_options` | 190 | 2 | 0 |  |
| `TopicPending` | 17 | 1 | 1 | Mantém as chaves legadas no chat principal e isola pendências nos tópicos. |
| `deep_action` | 48 | 1 | 1 |  |
| `protect_financial_content` | 194 | 1 | 1 | Política de transporte; não interfere no conteúdo ou nos cálculos. |
| `send_rich` | 199 | 1 | 1 | Retorna False só em rejeição explícita; timeout não duplica a mensagem. |
| `dispatch` | 64 | 1 | 0 |  |
| `rich_summary` | 61 | 1 | 0 |  |
| `scope_update` | 28 | 1 | 0 |  |

## Tudo que define

- classe `TopicPending` (L17, 10 linhas) — Mantém as chaves legadas no chat principal e isola pendências nos tópicos.
- `scope_update` (L28, 1 linhas)
- `deep_action` (L48, 12 linhas)
- `rich_summary` (L61, 2 linhas)
- `dispatch` (L64, 114 linhas)
- `_resume` (L179, 4 linhas)
- `thread_id` (L184, 5 linhas)
- `thread_options` (L190, 3 linhas)
- `protect_financial_content` (L194, 4 linhas) — Política de transporte; não interfere no conteúdo ou nos cálculos.
- `send_rich` (L199, 24 linhas) — Retorna False só em rejeição explícita; timeout não duplica a mensagem.

## Testes que usam (1)

- `tests/test_inovacoes_410.py`

## No mapa de rotas

- **Módulo (1):** [[mod_telegram_recursos.py-a9bf3|telegram_recursos.py]]
- **Funções no mapa (4):** [[fn_telegram_recursos.deep_action-f02e9|telegram_recursos.deep_action]], [[fn_telegram_recursos.dispatch-a2ef9|telegram_recursos.dispatch]], [[fn_telegram_recursos.send_rich-23541|telegram_recursos.send_rich]], [[fn_telegram_recursos.thread_id-d8fb8|telegram_recursos.thread_id]]
- **Chamadas de serviço (2):** [[fn_telegram_recursos._resume-ec321|telegram_recursos._resume]], [[fn_telegram_recursos.rich_summary-daab9|telegram_recursos.rich_summary]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
