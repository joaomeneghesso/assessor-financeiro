---
tipo: handler
arquivo: telegram_experiencia.py
linha: 4525
---
# _pay_account_screen

Resumo/detalhe de pagamento de uma conta; grava Session.month (l.3625).

`fn:ux._pay_account_screen`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3625
- (chama) [[fn_compromissos.calcular_resumo_pagamento_conta-dc584|compromissos.calcular_resumo_pagamento_conta]] 
- (chama) [[fn_compromissos.detalhar_pagamento_por_conta-62748|compromissos.detalhar_pagamento_por_conta]] 
- (chama) [[fn_ux._pay_summary_rich_body-7145b|ux._pay_summary_rich_body]] 
- (chama) [[act_pay_account-299dd|pay_account]] 
- (chama) [[act_pay_account_detail-6c538|pay_account_detail]] 
- (chama) [[act_pay_account_filter-642f0|pay_account_filter]] 
- (chama) [[act_view-1d8b8|view]] 

## Vem de
- (chama) [[fn_ux.fast_deterministic_query-fb2df|fast_deterministic_query]] quanto vou pagar <conta>
- (chama) [[act_pay_account-299dd|pay_account]] 
- (chama) [[act_pay_account_detail-6c538|pay_account_detail]] 
