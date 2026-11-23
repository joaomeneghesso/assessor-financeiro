---
tipo: handler
arquivo: telegram_experiencia.py
linha: 1758
---
# begin_invoice_payment

Inicia pagamento de fatura; grava Session.month = mês da fatura (l.1473).

`fn:ux.begin_invoice_payment`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.1473 s.month=mês da fatura
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 
- (navega) [[fn_ux.invoice_prompt-6a4d0|invoice_prompt]] 
- (chama) [[fn_services.calcular_resumo_fatura-b4797|services.calcular_resumo_fatura]] 
- (chama) [[fn_services.resolver_item_checklist-a2267|services.resolver_item_checklist]] 

## Vem de
- (chama) [[fn_ux.begin_invoice_payment_from_command-5d84f|begin_invoice_payment_from_command]] 
- (chama) [[act_invoice_begin-31c3f|invoice_begin]] 
- (chama) [[act_invoice_restart-21e5e|invoice_restart]] 
