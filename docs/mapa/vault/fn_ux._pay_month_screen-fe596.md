---
tipo: handler
arquivo: telegram_experiencia.py
linha: 4392
---
# _pay_month_screen

Resumo "QUANTO VOU PAGAR · <mês>" por conta; grava Session.month=month (l.3497).

`fn:ux._pay_month_screen`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3497
- (grava_estado) [[state_Session.pay_month_page-6ad4e|Session.pay_month_page]] 
- (chama) [[fn_ux._pay_month_open_items-25d5f|ux._pay_month_open_items]] 
- (chama) [[fn_compromissos.obter_itens_base_pagamentos_mes-4d0ba|compromissos.obter_itens_base_pagamentos_mes]] 
- (chama) [[fn_ux._pay_summary_rich_body-7145b|ux._pay_summary_rich_body]] 
- (chama) [[fn_compromissos.item_eh_fatura_cartao-05eac|compromissos.item_eh_fatura_cartao]] 
- (chama) [[fn_compromissos.calcular_resumo_pagamento_conta-dc584|compromissos.calcular_resumo_pagamento_conta]] 
- (chama) [[act_pay_month_page-dc8ea|pay_month_page]] 
- (chama) [[act_pay_month-b80f8|pay_month]] 
- (chama) [[act_view-1d8b8|view]] 
- (chama) [[act_pay_month_expand-8623d|pay_month_expand]] 
- (chama) [[act_pay_month_account_detail-c0214|pay_month_account_detail]] 

## Vem de
- (chama) [[fn_ux._ai_query_result-20fe1|_ai_query_result]] qtype payables
- (chama) [[act_pay_month-b80f8|pay_month]] 
- (chama) [[act_pay_month_expand-8623d|pay_month_expand]] 
- (chama) [[act_pay_month_page-dc8ea|pay_month_page]] 
