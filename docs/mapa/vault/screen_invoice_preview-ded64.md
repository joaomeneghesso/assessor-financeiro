---
tipo: screen
arquivo: telegram_experiencia.py
linha: 1535
---
# invoice_preview

Prévia do pagamento de fatura (revalida saldo).

`screen:invoice_preview`

## Vai para
- (chama) [[fn_services.resolver_item_checklist-a2267|services.resolver_item_checklist]] 
- (chama) [[fn_services.calcular_resumo_fatura-b4797|services.calcular_resumo_fatura]] 
- (navega) [[act_invoice_commit-7ad93|invoice_commit]] ✅ Confirmar pagamento
- (navega) [[act_invoice_edit_amount-537f4|invoice_edit_amount]] Editar valor
- (navega) [[act_invoice_edit_account-39359|invoice_edit_account]] Trocar conta pagadora
- (navega) [[act_invoice_restart-21e5e|invoice_restart]] Atualizar fatura
- (navega) [[act_cancel-c6497|cancel]] Cancelar

## Vem de
- (navega) [[act_invoice_account_select-4bf7f|invoice_account_select]] 
- (navega) [[act_invoice_preview-752d1|invoice_preview]] 
