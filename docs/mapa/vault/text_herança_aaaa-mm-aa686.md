---
tipo: text_trigger
arquivo: services.py
linha: 8646
---
# herança [aaaa-mm]

Também: saldo herdado, ponte do mês. Mês padrão = hoje.

`text:herança [aaaa-mm]`

## Vai para
- (chama) [[fn_services.validar_ano_mes-a072d|services.validar_ano_mes]] 
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] 
- (chama) [[fn_services.formatar_ano_mes_visual-b32b4|services.formatar_ano_mes_visual]] 
- (chama) [[fn_services.bloco_heranca_mes_anterior-6a843|services.bloco_heranca_mes_anterior]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8646
