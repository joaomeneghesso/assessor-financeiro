---
tipo: action
arquivo: telegram_experiencia.py
linha: 2892
---
# accounts_for

Seletor de conta para pay/history.

`act:accounts_for`

## Vai para
- (grava_estado) [[state_Session.filter_view-6b228|Session.filter_view]] 
- (grava_estado) [[state_Session.trail-b6f1c|Session.trail]] 
- (navega) [[screen_accounts-cc0c6|accounts]] 
- (le_estado) [[state_Session.view-a9ea1|Session.view]] 
- (le_estado) [[state_Session.month-7f614|Session.month]] 
- (le_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_pay_tools-19539|pay_tools]] Filtrar conta
- (navega) [[screen_history_tools-cc0f8|history_tools]] Filtrar conta
- (chama) [[fn_ux._pay_tools_screen-7fc89|_pay_tools_screen]] 
- (chama) [[fn_ux._history_tools_screen-c950e|_history_tools_screen]] 
