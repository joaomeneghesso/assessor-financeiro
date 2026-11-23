---
tipo: action
arquivo: telegram_experiencia.py
linha: 2981
---
# clear_pay_filters

Zera filtros de A pagar.

`act:clear_pay_filters`

## Vai para
- (grava_estado) [[state_Session.pay_filter-c235f|Session.pay_filter]] 
- (grava_estado) [[state_Session.pay_account_filter-280ee|Session.pay_account_filter]] 
- (navega) [[screen_pay-ee2a3|pay]] 
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_pay_tools-19539|pay_tools]] Limpar filtros
- (chama) [[fn_ux._pay_tools_screen-7fc89|_pay_tools_screen]] 
