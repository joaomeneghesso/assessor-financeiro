---
tipo: service_call
arquivo: assessor_orientacao.py
linha: 
---
# coletar

Função de assessor_orientacao.py (orient)

`fn:orientacao.coletar`

## Vai para
- (le_estado) [[state_Experience._retrato-dbb0d|Experience._retrato]] cache só dentro de um render
- (le_estado) [[state_Session.month-7f614|Session.month]] monta métricas/itens do s.month
- (chama) [[fn_ux.obligations-15fc7|obligations]] 
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] 
- (chama) [[fn_ux.transactions-60180|transactions]] 

## Vem de
- (chama) [[screen_home-111fe|home]] 
- (chama) [[screen_month_actions-bedf6|month_actions]] 
- (chama) [[screen_closing_details-60038|closing_details]] 
- (chama) [[screen_pay-ee2a3|pay]] 
- (chama) [[screen_plan-adfe6|plan]] 
- (chama) [[screen_agenda-a82fc|agenda]] 
- (chama) [[screen_recurring-7f11e|recurring]] 
- (chama) [[screen_dashboard-6ba51|dashboard]] 
- (chama) [[act_chart-efa97|chart]] 
