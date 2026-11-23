---
tipo: service
arquivo: assessor_orientacao.py
linha: 79
---
# assessor_orientacao.coletar

Retrato do mês (métricas, tx, obrigações, metas, insights) para uma renderização.

`fn:assessor_orientacao.coletar`

## Vai para
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] 81
- (le_estado) [[state_Session.month-7f614|Session.month]] s.month

## Vem de
- (chama) [[mod_assessor_orientacao.py-e9925|assessor_orientacao.py]] 
- (chama) [[fn_telegram_alertas._snapshot_alerta-02723|telegram_alertas._snapshot_alerta]] 
