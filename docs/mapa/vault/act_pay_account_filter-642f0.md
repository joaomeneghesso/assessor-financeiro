---
tipo: action
arquivo: telegram_experiencia.py
linha: 3006
---
# pay_account_filter

A pagar filtrado por conta: grava Session.month=action[2] e pay_account_filter.

`act:pay_account_filter`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.2509 s.month=action[2]
- (grava_estado) [[state_Session.pay_account_filter-280ee|Session.pay_account_filter]] 
- (grava_estado) [[state_Session.pay_filter-c235f|Session.pay_filter]] 
- (navega) [[screen_pay-ee2a3|pay]] 
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_pay_account-46888|pay_account]] A pagar filtrado
- (chama) [[fn_ux._pay_account_screen-545a8|_pay_account_screen]] 
