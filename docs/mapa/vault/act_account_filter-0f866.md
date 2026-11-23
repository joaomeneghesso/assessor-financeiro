---
tipo: action
arquivo: telegram_experiencia.py
linha: 3012
---
# account_filter

Aplica filtro de conta.

`act:account_filter`

## Vai para
- (grava_estado) [[state_Session.pay_account_filter-280ee|Session.pay_account_filter]] filter_view=pay
- (grava_estado) [[state_Session.history_account_filter-0cdca|Session.history_account_filter]] filter_view=history
- (grava_estado) [[state_Session.trail-b6f1c|Session.trail]] pop
- (navega) [[screen_pay-ee2a3|pay]] 
- (navega) [[screen_history-d40e7|history]] 
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (le_estado) [[state_Session.filter_view-6b228|Session.filter_view]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_accounts-cc0c6|accounts]] Todas as contas / <conta>
