---
tipo: handler
arquivo: telegram_experiencia.py
linha: 4510
---
# _pay_month_account_detail

Detalhe técnico da conta no mês; grava Session.month (l.3611).

`fn:ux._pay_month_account_detail`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3611
- (chama) [[fn_compromissos.detalhar_pagamento_por_conta-62748|compromissos.detalhar_pagamento_por_conta]] 
- (le_estado) [[state_Session.pay_month_page-6ad4e|Session.pay_month_page]] 
- (chama) [[act_pay_month_account_detail-c0214|pay_month_account_detail]] 
- (chama) [[act_pay_month_expand-8623d|pay_month_expand]] 
- (chama) [[act_pay_account-299dd|pay_account]] 
- (chama) [[act_view-1d8b8|view]] 

## Vem de
- (chama) [[act_pay_month_account_detail-c0214|pay_month_account_detail]] 
