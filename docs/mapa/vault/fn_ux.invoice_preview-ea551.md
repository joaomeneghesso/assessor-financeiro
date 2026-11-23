---
tipo: handler
arquivo: telegram_experiencia.py
linha: 1843
---
# invoice_preview

Prévia do pagamento da fatura (revalida saldo).

`fn:ux.invoice_preview`

## Vai para
- (chama) [[fn_services.resolver_item_checklist-a2267|services.resolver_item_checklist]] 
- (chama) [[fn_services.calcular_resumo_fatura-b4797|services.calcular_resumo_fatura]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (chama) [[fn_ux.invoice_prompt-6a4d0|invoice_prompt]] 
- (le_estado) [[state_Session.draft-81d88|Session.draft]] 
- (chama) [[act_invoice_commit-7ad93|invoice_commit]] 
- (chama) [[act_invoice_edit_amount-537f4|invoice_edit_amount]] 
- (chama) [[act_invoice_edit_account-39359|invoice_edit_account]] 
- (chama) [[act_cancel-c6497|cancel]] 
- (chama) [[act_invoice_restart-21e5e|invoice_restart]] 

## Vem de
- (chama) [[act_conflict_keep-95a36|conflict_keep]] 
- (chama) [[act_invoice_account_select-4bf7f|invoice_account_select]] 
- (chama) [[act_invoice_preview-752d1|invoice_preview]] 
- (chama) [[fn_ux.invoice_prompt-6a4d0|invoice_prompt]] 
