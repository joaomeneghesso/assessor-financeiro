---
tipo: handler
arquivo: telegram_experiencia.py
linha: 1795
---
# begin_invoice_payment_from_command

Comando de texto de pagamento de fatura.

`fn:ux.begin_invoice_payment_from_command`

## Vai para
- (chama) [[fn_services.resolver_fatura_checklist_por_nome-14c94|resolver_fatura_checklist_por_nome]] 
- (chama) [[fn_ux.begin_invoice_payment-d061f|begin_invoice_payment]] 

## Vem de
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
