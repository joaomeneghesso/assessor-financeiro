---
tipo: service
arquivo: services.py
linha: 11430
---
# services.calcular_saldo_mensal

Função de negócio (destino de roteamento).

`fn:services.calcular_saldo_mensal`

## Vai para
- (le_estado) [[state_CONTEXTO_CONSULTA-83d77|CONTEXTO_CONSULTA]] _consulta_cache(chave) usa o dict do contexto se existir
- (grava_estado) [[state_CONTEXTO_CONSULTA-83d77|CONTEXTO_CONSULTA]] memoriza resultado no cache do contexto atual
- (chama) [[fn_services._avaliar_heranca-4ea4d|services._avaliar_heranca]] 

## Vem de
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] via _calcular_metricas_resultado_mes
- (chama) [[fn_services.gerar_saldo_mes_ux-6c533|services.gerar_saldo_mes_ux]] 
