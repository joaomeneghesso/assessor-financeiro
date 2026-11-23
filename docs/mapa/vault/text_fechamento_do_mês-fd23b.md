---
tipo: text_trigger
arquivo: app.py
linha: 9188
---
# fechamento do mês

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:fechamento do mês`

## Vai para
- (chama) [[fn_services.gerar_fechamento_mensal_formatado-95fd9|services.gerar_fechamento_mensal_formatado]] 

## Vem de
- (navega) [[btn_Fechamento-d1cce|📄 Fechamento]] envia 'fechamento do mês'
- (chama) [[job_rotina_resumo_domingo-a471e|rotina_resumo_domingo]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9188
- (chama) [[mod_app.py-57fef|app.py]] resumo mensal app.py:5446
