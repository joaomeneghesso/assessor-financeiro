---
tipo: screen
arquivo: telegram_experiencia.py
linha: 1448
---
# review_details

Pendências de conciliação e qualidade dos registros.

`screen:review_details`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] título/consulta usa s.month
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] 
- (chama) [[fn_conciliacao.alvo-7b858|alvo]] 
- (chama) [[fn_ux.transactions-60180|transactions]] 
- (navega) [[act_reconcile_baseline_preview-fb5bf|reconcile_baseline_preview]] ✅ Meu saldo atual confere
- (navega) [[act_link_existing-2737a|link_existing]] Revisar #id
- (navega) [[act_filter-91736|filter]] 🔎 Revisar baixas antigas
- (navega) [[screen_reconciliations-256e3|reconciliations]] 🔗 Movimentos conciliados
- (navega) [[screen_history-d40e7|history]] Abrir histórico
- (navega) [[fn_ux.nav-29bea|Experience.nav]] nav
- (chama) [[fn_ux._reconciliation_review_summary-96c53|ux._reconciliation_review_summary]] 
- (navega) [[act_view-1d8b8|view]] 

## Vem de
- (navega) [[screen_review-185df|review]] 🔎 Ver pendências e detalhes
