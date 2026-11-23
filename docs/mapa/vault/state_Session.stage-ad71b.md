---
tipo: state
arquivo: telegram_experiencia.py
linha: 376
---
# Session.stage

Etapa do fluxo guiado ativo (amount, description, confirm, invoice_*, cash_setup_*, new_fixed_*, ask, search...). Decide se um texto vira resposta do fluxo.

`state:Session.stage`

## Vem de
- (le_estado) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] native_active
- (le_estado) [[fn_ux.prompt-41177|prompt]] 
- (grava_estado) [[act_view-1d8b8|view]] zera
- (grava_estado) [[act_back-bca78|back]] descarta
- (grava_estado) [[act_account_search-82984|account_search]] account_search
- (grava_estado) [[act_search-165fd|search]] search
- (grava_estado) [[act_ask-dbbdf|ask]] ask
- (grava_estado) [[act_learning_resume-96135|learning_resume]] 
- (grava_estado) [[act_edit-7bceb|edit]] 
- (grava_estado) [[act_balance_initial-82e49|balance_initial]] initial_balance
- (grava_estado) [[act_budget_start-ded37|budget_start]] budget_category
- (grava_estado) [[act_alert_hours-a41d6|alert_hours]] alert_hours
- (grava_estado) [[act_cancel-c6497|cancel]] zera
- (grava_estado) [[act_guided-cf3e7|guided]] zera
- (grava_estado) [[fn_ux.begin-7f489|begin]] 
- (le_estado) [[fn_ux.answer-a52eb|answer]] 
- (grava_estado) [[act_topic-518da|topic]] 
- (grava_estado) [[act_new_fixed_define_end-b9e31|new_fixed_define_end]] 
- (grava_estado) [[act_new_fixed_back-a5d76|new_fixed_back]] 
- (grava_estado) [[act_new_fixed_edit-fc7ba|new_fixed_edit]] 
- (grava_estado) [[act_new_fixed_cancel-e16bb|new_fixed_cancel]] 
- (grava_estado) [[act_new_fixed_commit-b9167|new_fixed_commit]] 
- (grava_estado) [[act_transaction-fab7d|transaction]] 
- (grava_estado) [[act_back_step-afc43|back_step]] 
- (le_estado) [[act_flow_resume-b920b|flow_resume]] 
- (le_estado) [[act_conflict_keep-95a36|conflict_keep]] 
- (grava_estado) [[act_conflict_start-3417b|conflict_start]] 
- (grava_estado) [[act_category_rule_remove-7bab7|category_rule_remove]] 
- (grava_estado) [[act_category_rule_remove_commit-35909|category_rule_remove_commit]] 
- (le_estado) [[act_account_choice_page-f85b1|account_choice_page]] 
- (grava_estado) [[act_cash_setup_new_account-43b33|cash_setup_new_account]] 
- (grava_estado) [[act_cash_setup_edit-4d66a|cash_setup_edit]] 
- (grava_estado) [[act_invoice_pay_total-92cc5|invoice_pay_total]] 
- (grava_estado) [[act_invoice_pay_partial-2e888|invoice_pay_partial]] 
- (grava_estado) [[act_invoice_back_choice-dd552|invoice_back_choice]] 
- (grava_estado) [[act_invoice_account_select-4bf7f|invoice_account_select]] 
- (grava_estado) [[act_invoice_edit_amount-537f4|invoice_edit_amount]] 
- (grava_estado) [[act_invoice_edit_account-39359|invoice_edit_account]] 
- (grava_estado) [[act_invoice_commit-7ad93|invoice_commit]] 
- (grava_estado) [[act_repeat-a98e8|repeat]] 
- (grava_estado) [[act_reconcile_baseline_preview-fb5bf|reconcile_baseline_preview]] 
- (grava_estado) [[act_reconcile_baseline_commit-6bad7|reconcile_baseline_commit]] 
- (grava_estado) [[act_save_hours-ad3d6|save_hours]] 
- (grava_estado) [[act_budget_cat-77d03|budget_cat]] 
- (grava_estado) [[act_save_balance-8b906|save_balance]] 
- (grava_estado) [[act_save_budget-c4116|save_budget]] 
- (grava_estado) [[act_keep_separate-a37e9|keep_separate]] 
- (grava_estado) [[act_commit_link-b8e95|commit_link]] 
- (grava_estado) [[act_commit-ada76|commit]] 
- (grava_estado) [[act_date_type-a560a|date_type]] 
- (grava_estado) [[fn_ux.preview-35809|preview]] 
- (le_estado) [[fn_ux.invoice_prompt-6a4d0|invoice_prompt]] 
- (grava_estado) [[fn_ux.invoice_preview-ea551|invoice_preview]] 
- (le_estado) [[fn_ux._new_fixed_prompt-ecd34|_new_fixed_prompt]] 
- (le_estado) [[fn_ux._flow_help_screen-a5285|_flow_help_screen]] 
- (grava_estado) [[fn_ux._cash_setup_start-b8255|_cash_setup_start]] 
- (grava_estado) [[fn_ux._new_fixed_preview-90ab6|_new_fixed_preview]] 
- (grava_estado) [[fn_ux._new_fixed_edit_menu-3488b|ux._new_fixed_edit_menu]] 
- (grava_estado) [[fn_ux.question_result-77118|question_result]] 
- (grava_estado) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
