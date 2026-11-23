---
tipo: service
arquivo: services.py
linha: 7700
---
# services.calcular_resumo_fatura

Função de negócio (destino de roteamento).

`fn:services.calcular_resumo_fatura`

## Vai para
- (chama) [[fn_compromissos.calcular_fatura_unificada-1dca9|compromissos.calcular_fatura_unificada]] 

## Vem de
- (chama) [[fn_telegram_registros.confirmar_pagamento_fatura-ded85|telegram_registros.confirmar_pagamento_fatura]] 
- (chama) [[fn_telegram_recursos.dispatch-a2ef9|telegram_recursos.dispatch]] 73 (invoice_origin)
- (chama) [[screen_invoice_preview-ded64|invoice_preview]] 
- (chama) [[fn_ux.begin_invoice_payment-d061f|begin_invoice_payment]] 
- (chama) [[fn_ux.invoice_preview-ea551|invoice_preview]] 
