---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 237
tags: [modulo, telegram-telas-e-conversa]
---
# telegram_visuais.py

> RC3.0.38 — painéis de leitura; não consultam nem alteram dados financeiros.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 237 · **Funções:** 16 · **Classes:** 0

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[telegram_experiencia.py]] — `painel`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `painel` | 123 | 1 | 4 | Painel de leitura compacto; recebe valores prontos do motor financeiro. |
| `font` | 23 | 0 | 1 |  |
| `moeda` | 72 | 0 | 1 | R$ 1.234,56; negativo '−R$ 1.234,56' (U+2212); zero negativo vira 'R$ 0,00'. |
| `normalizar_dinheiro` | 31 | 0 | 1 | Zero negativo nunca aparece: 'R$ -0,00' / '-R$ 0,00' / '−R$ 0,00' viram 'R$ 0,00'. |
| `texto` | 36 | 0 | 1 |  |

## Tudo que define

- `font` (L23, 6 linhas)
- `normalizar_dinheiro` (L31, 3 linhas) — Zero negativo nunca aparece: 'R$ -0,00' / '-R$ 0,00' / '−R$ 0,00' viram 'R$ 0,00'.
- `texto` (L36, 10 linhas)
- `_quebrar` (L48, 9 linhas)
- `_altura_linhas` (L59, 2 linhas)
- `linhas` (L63, 7 linhas) — Escreve texto quebrado em linhas; devolve o y logo abaixo do bloco.
- `moeda` (L72, 5 linhas) — R$ 1.234,56; negativo '−R$ 1.234,56' (U+2212); zero negativo vira 'R$ 0,00'.
- `_negativo` (L79, 2 linhas)
- `_canvas` (L83, 2 linhas)
- `_finalizar` (L87, 5 linhas)
- `_cabecalho` (L94, 5 linhas)
- `_hero` (L101, 6 linhas)
- `_card_largo` (L109, 12 linhas) — Cartão em largura total: rótulo em cima, valor grande embaixo (+ dica opcional).
- `painel` (L123, 47 linhas) — Painel de leitura compacto; recebe valores prontos do motor financeiro.
- `_metrica` (L172, 7 linhas)
- `painel_dashboard` (L181, 57 linhas) — Visão ampliada em blocos, com tipografia legível e navegação por assunto.

## Testes que usam (4)

- `tests/test_dashboard_metricas_412.py`
- `tests/test_dashboard_rota_entrega.py`
- `tests/test_help_aprender_dashboard_407.py`
- `tests/test_painel_png_legivel.py`

## No mapa de rotas

- **Módulo (1):** [[mod_telegram_visuais.py-cc99f|telegram_visuais.py]]
- **Funções no mapa (2):** [[fn_telegram_visuais.painel-9bbaf|telegram_visuais.painel]], [[fn_telegram_visuais.painel_dashboard-c9f1c|telegram_visuais.painel_dashboard]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
