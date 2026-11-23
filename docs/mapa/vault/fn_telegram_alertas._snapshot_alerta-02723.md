---
tipo: service
arquivo: telegram_alertas.py
linha: 190
---
# telegram_alertas._snapshot_alerta

Cria Experience temporária e chama orient.coletar em modo somente leitura.

`fn:telegram_alertas._snapshot_alerta`

## Vai para
- (chama) [[fn_assessor_orientacao.coletar-df8f0|assessor_orientacao.coletar]] 
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] via coletar

## Vem de
- (chama) [[fn_telegram_alertas.executar_janela-a11fc|telegram_alertas.executar_janela]] 
