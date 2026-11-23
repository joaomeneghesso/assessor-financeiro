---
tipo: action
arquivo: telegram_experiencia.py
linha: 3061
---
# invoice_commit

GRAVA pagamento de fatura (confirmar_pagamento_fatura); grava Session.month=mês da fatura.

`act:invoice_commit`

## Vai para
- (chama) [[fn_telegram_registros.confirmar_pagamento_fatura-ded85|telegram_registros.confirmar_pagamento_fatura]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.2570 s.month=mês da fatura
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (grava_estado) [[state_Session.last_event-a12b9|Session.last_event]] 
- (chama) [[fn_services.slug_banco_checklist-ba1f3|services.slug_banco_checklist]] 
- (le_estado) [[state_Session.trail-b6f1c|Session.trail]] 
- (navega) [[act_back-bca78|back]] botão da resposta
- (navega) [[act_view-1d8b8|view]] botão da resposta
- (navega) [[act_detail_obligation-b6e92|detail_obligation]] botão da resposta

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_invoice_preview-ded64|invoice_preview]] ✅ Confirmar pagamento
- (chama) [[fn_ux.invoice_preview-ea551|invoice_preview]] 
