---
tipo: state
arquivo: telegram_experiencia.py
linha: 373
---
# Session.draft

Rascunho de registro/pagamento de fatura/baixa. Descartado por back/cancel/ask/guided; suspenso por view/consulta.

`state:Session.draft`

## Vem de
- (le_estado) [[fn_ux.target_picker-0a39c|target_picker]] 
- (le_estado) [[fn_ux.prompt-41177|prompt]] 
- (le_estado) [[fn_ux.preview-35809|preview]] 
- (le_estado) [[fn_ux.invoice_prompt-6a4d0|invoice_prompt]] 
- (grava_estado) [[act_back-bca78|back]] descarta
- (grava_estado) [[act_ask-dbbdf|ask]] zera
- (grava_estado) [[act_commit-ada76|commit]] zera
- (grava_estado) [[act_invoice_commit-7ad93|invoice_commit]] 
- (grava_estado) [[act_cancel-c6497|cancel]] zera
- (grava_estado) [[act_guided-cf3e7|guided]] zera
- (grava_estado) [[fn_ux.begin-7f489|begin]] 
- (grava_estado) [[fn_ux.parse_draft-0ebfb|parse_draft]] 
- (grava_estado) [[fn_ux._suspend_flow-76c4a|_suspend_flow]] zera
- (grava_estado) [[fn_ux.begin_invoice_payment-d061f|begin_invoice_payment]] 
- (grava_estado) [[fn_ux.begin_settlement-f6619|begin_settlement]] 
- (le_estado) [[act_topic-518da|topic]] 
- (le_estado) [[act_view-1d8b8|view]] 
- (le_estado) [[act_back_step-afc43|back_step]] 
- (le_estado) [[act_flow_resume-b920b|flow_resume]] 
- (le_estado) [[act_conflict_keep-95a36|conflict_keep]] 
- (grava_estado) [[act_conflict_start-3417b|conflict_start]] 
- (grava_estado) [[act_cash_setup_new_account-43b33|cash_setup_new_account]] 
- (grava_estado) [[act_invoice_pay_total-92cc5|invoice_pay_total]] 
- (grava_estado) [[act_invoice_pay_partial-2e888|invoice_pay_partial]] 
- (le_estado) [[act_invoice_back_choice-dd552|invoice_back_choice]] 
- (grava_estado) [[act_invoice_account_select-4bf7f|invoice_account_select]] 
- (grava_estado) [[act_invoice_edit_amount-537f4|invoice_edit_amount]] 
- (le_estado) [[act_invoice_edit_account-39359|invoice_edit_account]] 
- (grava_estado) [[act_repeat-a98e8|repeat]] 
- (grava_estado) [[act_reconcile_baseline_preview-fb5bf|reconcile_baseline_preview]] 
- (grava_estado) [[act_balance_initial-82e49|balance_initial]] 
- (grava_estado) [[act_simulate_variant-afc9e|simulate_variant]] 
- (le_estado) [[act_pick_target-407d8|pick_target]] 
- (grava_estado) [[act_choose_target-6f13c|choose_target]] 
- (grava_estado) [[act_keep_separate-a37e9|keep_separate]] 
- (grava_estado) [[act_commit_link-b8e95|commit_link]] 
- (grava_estado) [[act_edit-7bceb|edit]] 
- (grava_estado) [[act_search-165fd|search]] 
- (grava_estado) [[act_date_type-a560a|date_type]] 
- (le_estado) [[fn_ux.invoice_preview-ea551|invoice_preview]] 
- (le_estado) [[fn_ux._edit_menu_screen-ff416|_edit_menu_screen]] 
- (le_estado) [[fn_ux.installment_schedule-6e2cc|installment_schedule]] 
- (le_estado) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
