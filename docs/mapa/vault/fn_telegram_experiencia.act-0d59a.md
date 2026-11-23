---
tipo: service
arquivo: telegram_experiencia.py
linha: 2818
---
# telegram_experiencia.act

Despachante de ações de botão/rota: ('view', X) renderiza tela com s.month atual (NÃO reseta).

`fn:telegram_experiencia.act`

## Vai para
- (chama) [[fn_telegram_experiencia.render-aa635|telegram_experiencia.render]] kind=='view' 2814-2822: s.month intocado
- (grava_estado) [[state_Session.month-7f614|Session.month]] 'month' (2823), 'current_month' (2824), dashboard_month (2363)
- (chama) [[fn_telegram_recursos.dispatch-a2ef9|telegram_recursos.dispatch]] 2338-2340

## Vem de
- (chama) [[text_quanto_vou_pagar_ux2_aaaa-mm-714dc|quanto vou pagar [aaaa-mm] (UX2)]] ('view','pay')
- (chama) [[cmd_menu-be698|/menu]] app.py:4343 ('view','home')
- (chama) [[text_botões_view_X_Início-cb16d|botões ('view', X)]] 
- (chama) [[fn_telegram_alertas.callback-80f31|telegram_alertas.callback]] run_experience('act'|'render')
- (navega) [[fn_telegram_recursos.deep_action-f02e9|telegram_recursos.deep_action]] app.start: run_experience('render'|'act') (4365)
