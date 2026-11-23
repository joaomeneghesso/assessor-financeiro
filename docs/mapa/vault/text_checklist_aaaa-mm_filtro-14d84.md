---
tipo: text_trigger
arquivo: services.py
linha: 8638
---
# checklist [aaaa-mm|filtro]

Também: lista pagamentos, pagamentos.

`text:checklist [aaaa-mm|filtro]`

## Vai para
- (chama) [[fn_services.parsear_comando_checklist-aaf64|services.parsear_comando_checklist]] 
- (chama) [[fn_services.gerar_checklist_pagamentos-1bfb3|services.gerar_checklist_pagamentos]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8638
