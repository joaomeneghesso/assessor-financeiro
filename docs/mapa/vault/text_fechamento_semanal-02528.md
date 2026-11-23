---
tipo: text_trigger
arquivo: app.py
linha: 9185
---
# fechamento semanal

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:fechamento semanal`

## Vai para
- (chama) [[fn_services.gerar_fechamento_semanal_formatado-bd58c|services.gerar_fechamento_semanal_formatado]] 

## Vem de
- (chama) [[job_rotina_resumo_domingo-a471e|rotina_resumo_domingo]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9185
- (chama) [[mod_app.py-57fef|app.py]] resumo semanal app.py:5445
