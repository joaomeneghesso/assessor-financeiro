---
tipo: text_trigger
arquivo: services.py
linha: 9012
---
# pagar no <banco> [em aaaa-mm]

Atalho de quanto vou pagar no banco.

`text:pagar no <banco> [em aaaa-mm]`

## Vai para
- (chama) [[fn_compromissos.resumo_pagamento_por_conta-04e09|compromissos.resumo_pagamento_por_conta]] 
- (chama) [[fn_services.validar_ano_mes-a072d|services.validar_ano_mes]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9012
