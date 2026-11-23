---
tipo: service
arquivo: compromissos.py
linha: 1846
---
# compromissos.resumo_pagamento_mes_consolidado

Função de negócio (destino de roteamento).

`fn:compromissos.resumo_pagamento_mes_consolidado`

## Vai para
- (chama) [[fn_compromissos.obter_itens_base_pagamentos_mes-4d0ba|compromissos.obter_itens_base_pagamentos_mes]] 1771
- (chama) [[fn_compromissos.calcular_resumo_pagamento_conta-dc584|compromissos.calcular_resumo_pagamento_conta]] 1796 (por conta)
- (chama) [[fn_compromissos.item_entra_no_quanto_vou_pagar-0abd6|compromissos.item_entra_no_quanto_vou_pagar]] 

## Vem de
- (chama) [[text_quanto_vou_pagar-9e130|quanto vou pagar]] 
