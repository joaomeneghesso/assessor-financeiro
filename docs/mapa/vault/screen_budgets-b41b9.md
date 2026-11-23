---
tipo: screen
arquivo: telegram_experiencia.py
linha: 1379
---
# budgets

Limites por categoria vs gasto no mês.

`screen:budgets`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] título/consulta usa s.month
- (chama) [[fn_db.listar_metas-42a00|listar_metas]] 
- (chama) [[fn_ux.transactions-60180|transactions]] 
- (navega) [[act_budget_start-ded37|budget_start]] Criar / ajustar limite
- (navega) [[act_chart-efa97|chart]] Ver gráfico
- (navega) [[act_legacy-00431|legacy]] Lista completa
- (navega) [[fn_ux.nav-29bea|Experience.nav]] nav
- (chama) [[fn_orientacao.situacao_limites-eb39b|orientacao.situacao_limites]] 
- (chama) [[fn_orientacao.barra-bfa5b|orientacao.barra]] 

## Vem de
- (navega) [[screen_attention-ebc03|attention]] Resolver/conferir
- (navega) [[screen_planning_tools-d534b|planning_tools]] 🎯 Limites
- (navega) [[act_save_budget-c4116|save_budget]] 
- (navega) [[act_cancel-c6497|cancel]] 
