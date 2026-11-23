---
tipo: handler
arquivo: telegram_experiencia.py
linha: 1809
---
# invoice_prompt

Tela de etapas do pagamento de fatura (choice/amount/account).

`fn:ux.invoice_prompt`

## Vai para
- (le_estado) [[state_Session.draft-81d88|Session.draft]] 
- (navega) [[act_invoice_pay_total-92cc5|invoice_pay_total]] Usar saldo restante
- (navega) [[act_invoice_pay_partial-2e888|invoice_pay_partial]] Informar outro valor
- (navega) [[act_invoice_account_select-4bf7f|invoice_account_select]] <conta>
- (navega) [[act_invoice_account_page-04733|invoice_account_page]] ‹ Contas / Mais contas ›
- (navega) [[act_invoice_back_choice-dd552|invoice_back_choice]] ‹ Voltar
- (navega) [[act_cancel-c6497|cancel]] Cancelar
- (chama) [[fn_ux.accounts-08856|accounts]] 
- (grava_estado) [[state_Session.account_choice_page-45779|Session.account_choice_page]] 
- (chama) [[fn_ux.invoice_preview-ea551|invoice_preview]] 
- (le_estado) [[state_Session.stage-ad71b|Session.stage]] 

## Vem de
- (navega) [[act_invoice_pay_total-92cc5|invoice_pay_total]] 
- (navega) [[act_invoice_pay_partial-2e888|invoice_pay_partial]] 
- (navega) [[act_invoice_back_choice-dd552|invoice_back_choice]] 
- (navega) [[act_invoice_account_page-04733|invoice_account_page]] 
- (navega) [[act_invoice_edit_amount-537f4|invoice_edit_amount]] 
- (navega) [[act_invoice_edit_account-39359|invoice_edit_account]] 
- (navega) [[fn_ux.answer-a52eb|answer]] 
- (navega) [[fn_ux.begin_invoice_payment-d061f|begin_invoice_payment]] 
- (chama) [[act_conflict_keep-95a36|conflict_keep]] 
- (chama) [[fn_ux.invoice_preview-ea551|invoice_preview]] 
