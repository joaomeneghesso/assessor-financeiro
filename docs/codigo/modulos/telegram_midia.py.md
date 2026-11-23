---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 311
tags: [modulo, telegram-telas-e-conversa]
---
# telegram_midia.py

> Recepção local de mídia: reconhecimento -> revisão -> formulário existente.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 311 · **Funções:** 10 · **Classes:** 1

## Usa

- [[config.py]]
- [[database.py]]
- [[money.py]] *(importação tardia, dentro de função)*
- [[registro_conversa.py]] *(importação tardia, dentro de função)*
- [[services.py]] *(importação tardia, dentro de função)*
- [[telegram_execucao.py]]
- [[telegram_experiencia.py]] *(importação tardia, dentro de função)*
- [[telegram_streaming.py]] *(importação tardia, dentro de função)*
- [[transcricao_audio.py]] *(importação tardia, dentro de função)*

## Usado por

- [[app.py]] — `receive`
- [[telegram_experiencia.py]] — `_transfer_screen`, `answer`, `dispatch`
- [[tools__medir_desempenho.py|tools/medir_desempenho.py]] — `reconhecer_foto`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `receive` | 261 | 1 | 1 |  |
| `reconhecer_foto` | 19 | 1 | 1 |  |
| `_transfer_screen` | 79 | 1 | 0 |  |
| `answer` | 233 | 1 | 0 | Edita um único campo da transferência reconhecida, sem gravá-la. |
| `dispatch` | 184 | 1 | 0 |  |
| `receipt_fields` | 50 | 0 | 2 | Só reconhece valores inequívocos; não escolhe banco de origem/destino. |
| `MediaError` | 16 | 0 | 1 |  |
| `review` | 107 | 0 | 1 |  |

## Tudo que define

- classe `MediaError` (L16, 1 linhas)
- `reconhecer_foto` (L19, 19 linhas)
- `_reconhecer_foto_tesseract` (L39, 10 linhas) — Linux (servidor): Tesseract local em português; mesmo contrato do OCR do Windows.
- `receipt_fields` (L50, 15 linhas) — Só reconhece valores inequívocos; não escolhe banco de origem/destino.
- `audio_kind_hint` (L66, 12 linhas) — Infere uma intenção explícita sem executar qualquer movimentação.
- `_transfer_screen` (L79, 27 linhas)
- `review` (L107, 60 linhas)
- `_draft_from_media` (L168, 15 linhas)
- `dispatch` (L184, 48 linhas)
- `answer` (L233, 27 linhas) — Edita um único campo da transferência reconhecida, sem gravá-la.
- `receive` (L261, 51 linhas)

## Testes que usam (2)

- `tests/test_inovacoes_410.py`
- `tests/test_portabilidade_linux.py`

## No mapa de rotas

- **Módulo (1):** [[mod_telegram_midia.py-d20ab|telegram_midia.py]]
- **Estado da sessão (1):** [[state_Session.media_review-1b659|Session.media_review]]
- **Funções no mapa (7):** [[fn_telegram_midia._draft_from_media-fe37a|telegram_midia._draft_from_media]], [[fn_telegram_midia.answer-67dec|telegram_midia.answer]], [[fn_telegram_midia.audio_kind_hint-23262|telegram_midia.audio_kind_hint]], [[fn_telegram_midia.dispatch-fb1f2|telegram_midia.dispatch]], [[fn_telegram_midia.receipt_fields-e0eb3|telegram_midia.receipt_fields]], [[fn_telegram_midia.reconhecer_foto-8734c|telegram_midia.reconhecer_foto]], [[fn_telegram_midia.review-9d355|telegram_midia.review]]
- **Tratadores (1):** [[fn_telegram_midia.receive-25423|telegram_midia.receive]]

## Documentos que citam

- [[reavaliacao/03_seguranca_privacidade]]
- [[reavaliacao/07_inventario_gravacao_legado]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
