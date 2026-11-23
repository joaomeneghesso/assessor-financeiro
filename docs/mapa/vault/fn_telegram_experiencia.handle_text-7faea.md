---
tipo: service
arquivo: telegram_experiencia.py
linha: 3755
---
# telegram_experiencia.handle_text

Roteador de texto da UX2: atalhos (menu/a pagar/...), regex 'quanto vou pagar [aaaa-mm]' (2954) e perguntas naturais.

`fn:telegram_experiencia.handle_text`

## Vai para
- (chama) [[text_quanto_vou_pagar_ux2_aaaa-mm-714dc|quanto vou pagar [aaaa-mm] (UX2)]] 2954
- (chama) [[text_menu_início_a_pagar_atalhos_UX2-88d1a|menu|inicio|central|a pagar|histórico|análises (texto)]] 2932
- (chama) [[fn_assessor_orientacao.reconhecer_pergunta-5191e|assessor_orientacao.reconhecer_pergunta]] 2971
- (chama) [[fn_telegram_aprendizado.route-d257a|telegram_aprendizado.route]] 2912 (antes de qualquer outra regra)
- (chama) [[fn_telegram_experiencia.parse_draft-28bf2|telegram_experiencia.parse_draft]] 2974/2984 gastei|recebi|comprei -> rascunho com confirmação

## Vem de
- (chama) [[fn_telegram_experiencia.dispatch_text-ef266|telegram_experiencia.dispatch_text]] 4193 caso contrário
