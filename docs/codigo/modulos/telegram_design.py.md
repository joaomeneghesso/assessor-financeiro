---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 415
tags: [modulo, telegram-telas-e-conversa]
---
# telegram_design.py

> Apresentação Telegram sem I/O, IA ou regras financeiras.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 415 · **Funções:** 22 · **Classes:** 0

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[app.py]] — `button_label`, `button_style`, `legacy_pages`, `mask_money`, `message_html`
- [[assessor_orientacao.py]] — `plural`
- [[telegram_alertas.py]] — `message_html`
- [[telegram_experiencia.py]] — `button_label`, `button_style`, `due_chip`, `heading`, `mask_money`, `message_html`, `money_sinal`, `pct` +9
- [[telegram_recursos.py]] — `rich_table`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `message_html` | 243 | 3 | 1 | Mensagens diretas (PIN, erros, etapas e avisos): escape antes do HTML. |
| `button_label` | 92 | 2 | 3 | Decoração apenas no envio: o texto digitado e o callback ficam intactos. |
| `button_style` | 358 | 2 | 1 | Cores são redundantes com rótulos: azul ação, verde confirmação, vermelho remoção. |
| `mask_money` | 60 | 2 | 1 | Troca todo valor monetário por ••••. ``bare`` inclui 210,00 sem R$ (rótulos de botão). |
| `plural` | 66 | 2 | 1 | '1 conta' / '3 contas' / '0 contas'; plural_ explícito para irregulares (item → itens). |
| `rich_table` | 330 | 2 | 1 | Tabela segura com total destacado pelo tema nativo do Telegram. |
| `present_text` | 221 | 1 | 2 | Uniformiza somente cabeçalhos gerados; nunca interpreta valores ou ações. |
| `due_chip` | 83 | 1 | 1 | Chip de vencimento (emoji + palavra no texto que o acompanha). |
| `legacy_pages` | 248 | 1 | 1 | Apresenta relatórios de texto depois de o adaptador extrair seus comandos. |
| `money_sinal` | 73 | 1 | 1 | 'R$ -1.234,56' → '−R$ 1.234,56' (U+2212). Só para a camada de UX. |
| `pct` | 78 | 1 | 1 | Percentual com vírgula decimal: 277.2 → '277,2%'. |
| `screen_styles` | 173 | 1 | 1 | Estilos de uma tela inteira: [ [(label, action)] ] -> [ [style] ]. |
| `superscript_number` | 9 | 1 | 1 | Número inteiro não negativo em algarismos sobrescritos Unicode. |
| `heading` | 216 | 1 | 0 |  |
| `registration_progress` | 404 | 1 | 0 | Etapas lógicas: dados → pagamento → data → conferência. |
| `report_html` | 293 | 1 | 0 | Relatórios nativos curtos: substitui alinhamento monoespaçado por linhas. |
| `rich_message_html` | 304 | 1 | 0 | Converte uma tela HTML existente em blocos de Rich Message. |
| `selected_style` | 396 | 1 | 0 | Realça o filtro atual sem alterar seu estado. |

## Tudo que define

- `superscript_number` (L9, 6 linhas) — Número inteiro não negativo em algarismos sobrescritos Unicode.
- `_with_icon` (L42, 8 linhas)
- `mask_money` (L60, 4 linhas) — Troca todo valor monetário por ••••. ``bare`` inclui 210,00 sem R$ (rótulos de botão).
- `plural` (L66, 5 linhas) — '1 conta' / '3 contas' / '0 contas'; plural_ explícito para irregulares (item → itens).
- `money_sinal` (L73, 3 linhas) — 'R$ -1.234,56' → '−R$ 1.234,56' (U+2212). Só para a camada de UX.
- `pct` (L78, 3 linhas) — Percentual com vírgula decimal: 277.2 → '277,2%'.
- `due_chip` (L83, 7 linhas) — Chip de vencimento (emoji + palavra no texto que o acompanha).
- `button_label` (L92, 52 linhas) — Decoração apenas no envio: o texto digitado e o callback ficam intactos.
- `_is_cancel` (L165, 6 linhas)
- `screen_styles` (L173, 16 linhas) — Estilos de uma tela inteira: [ [(label, action)] ] -> [ [style] ].
- `_confirms` (L191, 6 linhas)
- `_legacy_kind` (L199, 15 linhas) — Classifica um comando legado de botão: confirm, cancel, destroy ou None.
- `heading` (L216, 3 linhas)
- `present_text` (L221, 20 linhas) — Uniformiza somente cabeçalhos gerados; nunca interpreta valores ou ações.
- `message_html` (L243, 3 linhas) — Mensagens diretas (PIN, erros, etapas e avisos): escape antes do HTML.
- `legacy_pages` (L248, 43 linhas) — Apresenta relatórios de texto depois de o adaptador extrair seus comandos.
- `report_html` (L293, 9 linhas) — Relatórios nativos curtos: substitui alinhamento monoespaçado por linhas.
- `rich_message_html` (L304, 24 linhas) — Converte uma tela HTML existente em blocos de Rich Message.
- `rich_table` (L330, 26 linhas) — Tabela segura com total destacado pelo tema nativo do Telegram.
- `button_style` (L358, 36 linhas) — Cores são redundantes com rótulos: azul ação, verde confirmação, vermelho remoção.
- `selected_style` (L396, 6 linhas) — Realça o filtro atual sem alterar seu estado.
- `registration_progress` (L404, 12 linhas) — Etapas lógicas: dados → pagamento → data → conferência.

## Testes que usam (4)

- `tests/test_apresentacao_telegram_406.py`
- `tests/test_botoes_confirmacao.py`
- `tests/test_privacidade_formatacao_fase1.py`
- `tests/test_tabelas_financeiras_rich.py`

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
