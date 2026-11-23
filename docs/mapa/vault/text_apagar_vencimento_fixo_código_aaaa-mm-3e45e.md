---
tipo: text_trigger
arquivo: services.py
linha: 8551
---
# apagar vencimento fixo <código> [aaaa-mm]

Remove data de pagamento padrão/mensal.

`text:apagar vencimento fixo <código> [aaaa-mm]`

## Vai para
- (chama) [[fn_services.apagar_data_pagamento_checklist_formatado-1db1a|services.apagar_data_pagamento_checklist_formatado]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8551
