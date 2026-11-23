---
tipo: service
arquivo: compromissos.py
linha: 1626
---
# compromissos.calcular_resumo_pagamento_conta

Função de negócio (destino de roteamento).

`fn:compromissos.calcular_resumo_pagamento_conta`

## Vai para
- (chama) [[fn_compromissos.calcular_fatura_unificada-1dca9|compromissos.calcular_fatura_unificada]] 
- (chama) [[fn_compromissos.obter_itens_base_pagamentos_mes-4d0ba|compromissos.obter_itens_base_pagamentos_mes]] 

## Vem de
- (chama) [[fn_compromissos.resumo_pagamento_mes_consolidado-9efcf|compromissos.resumo_pagamento_mes_consolidado]] 1796 (por conta)
- (chama) [[fn_compromissos.resumo_pagamento_por_conta-04e09|compromissos.resumo_pagamento_por_conta]] 
- (chama) [[fn_compromissos.detalhar_pagamento_por_conta-62748|compromissos.detalhar_pagamento_por_conta]] 
- (chama) [[screen_pay_month-39a6a|pay_month]] 
- (chama) [[screen_pay_account-46888|pay_account]] 
- (chama) [[fn_ux._pay_month_screen-fe596|_pay_month_screen]] 
- (chama) [[fn_ux._pay_account_screen-545a8|_pay_account_screen]] 
