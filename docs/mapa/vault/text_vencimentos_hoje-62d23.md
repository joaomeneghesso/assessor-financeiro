---
tipo: text_trigger
arquivo: app.py
linha: 8555
---
# vencimentos hoje

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:vencimentos hoje`

## Vai para
- (chama) [[fn_services.gerar_lembrete_pagamentos_data-2b081|services.gerar_lembrete_pagamentos_data]] 

## Vem de
- (chama) [[job_rotina_lembrete_pagamentos_diario-95ac7|rotina_lembrete_pagamentos_diario]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8555
- (chama) [[mod_app.py-57fef|app.py]] lembrete diário app.py:5401
