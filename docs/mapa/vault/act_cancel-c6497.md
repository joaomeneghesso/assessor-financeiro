---
tipo: action
arquivo: telegram_experiencia.py
linha: 3366
---
# cancel

Cancela fluxo; limpa stage/draft/settings_draft; volta a tela conforme _cancel_view/stage.

`act:cancel`

## Vai para
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] zera
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] zera
- (grava_estado) [[state_Session.settings_draft-703dd|Session.settings_draft]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] restaura do trail só p/ invoice_/account_search
- (grava_estado) [[state_Session.media_review-1b659|Session.media_review]] 
- (navega) [[screen_register-1389d|register]] padrão
- (navega) [[screen_pay-ee2a3|pay]] 
- (navega) [[screen_receivables-eb894|receivables]] 
- (navega) [[screen_history-d40e7|history]] 
- (navega) [[screen_assistant-c05b6|assistant]] 
- (navega) [[screen_alerts-313c9|alerts]] 
- (navega) [[screen_budgets-b41b9|budgets]] 
- (navega) [[screen_balance-64c54|balance]] 
- (navega) [[screen_review-185df|review]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (grava_estado) [[state_Session.view-a9ea1|Session.view]] 
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (le_estado) [[state_Session.trail-b6f1c|Session.trail]] 
- (le_estado) [[state_Session.filter_view-6b228|Session.filter_view]] 
- (navega) [[act_view-1d8b8|view]] botão da resposta
- (navega) [[act_cash_accounts-a48cb|cash_accounts]] botão da resposta

## Vem de
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
- (chama) [[cmd_cancelar-18e66|/cancelar]] 
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_question-e9cf8|question]] Cancelar
- (navega) [[fn_ux.target_picker-0a39c|target_picker]] Cancelar
- (navega) [[fn_ux.prompt-41177|prompt]] Cancelar
- (navega) [[fn_ux.preview-35809|preview]] Cancelar
- (navega) [[screen_edit_menu-328c2|edit_menu]] Cancelar
- (navega) [[screen_installment_schedule-61a0b|installment_schedule]] Cancelar
- (navega) [[fn_ux.invoice_prompt-6a4d0|invoice_prompt]] Cancelar
- (navega) [[screen_invoice_preview-ded64|invoice_preview]] Cancelar
- (navega) [[fn_ux._flow_help_screen-a5285|_flow_help_screen]] Cancelar registro
- (navega) [[act_reconcile_baseline_preview-fb5bf|reconcile_baseline_preview]] Cancelar
- (navega) [[act_cash_setup_new_account-43b33|cash_setup_new_account]] botão da resposta
- (navega) [[act_account_search-82984|account_search]] botão da resposta
- (navega) [[act_alert_hours-a41d6|alert_hours]] botão da resposta
- (navega) [[act_budget_start-ded37|budget_start]] botão da resposta
- (navega) [[act_budget_cat-77d03|budget_cat]] botão da resposta
- (navega) [[act_balance_initial-82e49|balance_initial]] botão da resposta
- (navega) [[act_dup_view-7ad35|dup_view]] botão da resposta
- (chama) [[fn_ux.invoice_preview-ea551|invoice_preview]] 
- (chama) [[fn_ux._edit_menu_screen-ff416|_edit_menu_screen]] 
- (chama) [[fn_ux.installment_schedule-6e2cc|installment_schedule]] 
