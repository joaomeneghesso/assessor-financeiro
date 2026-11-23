---
tipo: service
arquivo: compromissos.py
linha: 1728
---
# compromissos.detalhar_pagamento_por_conta

Função de negócio (destino de roteamento).

`fn:compromissos.detalhar_pagamento_por_conta`

## Vai para
- (chama) [[fn_compromissos.calcular_fatura_unificada-1dca9|compromissos.calcular_fatura_unificada]] 
- (chama) [[fn_compromissos.calcular_resumo_pagamento_conta-dc584|compromissos.calcular_resumo_pagamento_conta]] 

## Vem de
- (chama) [[text_detalhar_quanto_vou_pagar_no_banco_em_aaaa-mm-c0cb1|detalhar quanto vou pagar no <banco> [em aaaa-mm]]] 
- (chama) [[screen_pay_month_account_detail-15b60|pay_month_account_detail]] 
- (chama) [[screen_pay_account-46888|pay_account]] 
- (chama) [[fn_ux._pay_month_account_detail-faa0e|_pay_month_account_detail]] 
- (chama) [[fn_ux._pay_account_screen-545a8|_pay_account_screen]] 
