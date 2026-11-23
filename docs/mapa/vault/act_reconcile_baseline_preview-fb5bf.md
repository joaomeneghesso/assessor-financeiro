---
tipo: action
arquivo: telegram_experiencia.py
linha: 3094
---
# reconcile_baseline_preview

Prévia de nova base de conciliação; força mês corrente.

`act:reconcile_baseline_preview`

## Vai para
- (navega) [[act_reconcile_baseline_commit-6bad7|reconcile_baseline_commit]] ✅ Confirmar nova base
- (navega) [[act_cancel-c6497|cancel]] Cancelar
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.2597 força mês corrente
- (grava_estado) [[state_Session.settings_draft-703dd|Session.settings_draft]] 
- (chama) [[fn_ux._reconciliation_review_summary-96c53|ux._reconciliation_review_summary]] 
- (chama) [[fn_db.buscar_saldo_mensal-82b9a|db.buscar_saldo_mensal]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (navega) [[act_view-1d8b8|view]] botão da resposta

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_review_details-b6002|review_details]] ✅ Meu saldo atual confere
