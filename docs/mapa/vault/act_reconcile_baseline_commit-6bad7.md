---
tipo: action
arquivo: telegram_experiencia.py
linha: 3122
---
# reconcile_baseline_commit

GRAVA nova base (orient.configurar_saldo).

`act:reconcile_baseline_commit`

## Vai para
- (chama) [[fn_orientacao.configurar_saldo-11f0c|configurar_saldo]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.2633 mês corrente
- (navega) [[screen_home-111fe|home]] 
- (chama) [[fn_ux._reconciliation_review_summary-96c53|ux._reconciliation_review_summary]] 
- (grava_estado) [[state_Session.settings_draft-703dd|Session.settings_draft]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] 
- (navega) [[act_view-1d8b8|view]] botão da resposta

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[act_reconcile_baseline_preview-fb5bf|reconcile_baseline_preview]] ✅ Confirmar nova base
