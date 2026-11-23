---
tipo: action
arquivo: telegram_experiencia.py
linha: 3060
---
# invoice_restart

Reabre pagamento da fatura.

`act:invoice_restart`

## Vai para
- (chama) [[fn_ux.begin_invoice_payment-d061f|begin_invoice_payment]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_invoice_preview-ded64|invoice_preview]] Atualizar fatura
- (chama) [[fn_ux.invoice_preview-ea551|invoice_preview]] 
