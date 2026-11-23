---
tipo: service
arquivo: dashboard_metricas.py
linha: 60
---
# dashboard_metricas.enriquecer

Enriquece spec do dashboard (home/evolution/diagnóstico) com séries e insights; read_only_mode + contexto_consulta.

`fn:dashboard_metricas.enriquecer`

## Vai para
- (chama) [[fn_dashboard_metricas.registros-637cc|dashboard_metricas.registros]] 
- (chama) [[fn_consulta_cache.contexto_consulta-9f519|consulta_cache.contexto_consulta]] 21
- (chama) [[fn_saldo_resumo.resumir_saldo-111a2|saldo_resumo.resumir_saldo]] 
- (chama) [[fn_database.read_only_mode-0854f|database.read_only_mode]] 
- (le_estado) [[state_Session.month-7f614|Session.month]] month=s.month (18)

## Vem de
- (chama) [[mod_dashboard_metricas.py-87582|dashboard_metricas.py]] 
- (chama) [[mod_telegram_experiencia.py-c6fa1|telegram_experiencia.py]] telegram_experiencia.py:2752
- (chama) [[screen_dashboard-6ba51|dashboard]] 
- (chama) [[act_chart-efa97|chart]] 
