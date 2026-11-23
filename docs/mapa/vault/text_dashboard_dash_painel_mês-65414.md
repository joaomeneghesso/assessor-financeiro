---
tipo: text_trigger
arquivo: services.py
linha: 8668
---
# dashboard|dash|painel [mês]

PNG do dashboard. No Telegram UX2 dashboard_route intercepta antes.

`text:dashboard|dash|painel [mês]`

## Vai para
- (chama) [[fn_services.parsear_comando_dashboard-142c3|services.parsear_comando_dashboard]] 
- (chama) [[fn_services.gerar_dashboard_visual_mes-3e58e|services.gerar_dashboard_visual_mes]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8668
