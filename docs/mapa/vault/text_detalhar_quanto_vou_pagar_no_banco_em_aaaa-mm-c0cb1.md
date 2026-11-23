---
tipo: text_trigger
arquivo: services.py
linha: 8991
---
# detalhar quanto vou pagar no <banco> [em aaaa-mm]

Também 'ver detalhes ...'. Só aceita AAAA-MM.

`text:detalhar quanto vou pagar no <banco> [em aaaa-mm]`

## Vai para
- (chama) [[fn_compromissos.detalhar_pagamento_por_conta-62748|compromissos.detalhar_pagamento_por_conta]] 
- (chama) [[fn_services.validar_ano_mes-a072d|services.validar_ano_mes]] 

## Vem de
- (navega) [[text_quanto_vou_pagar-9e130|quanto vou pagar]] mesma família
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8991
