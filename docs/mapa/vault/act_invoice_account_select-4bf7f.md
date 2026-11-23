---
tipo: action
arquivo: telegram_experiencia.py
linha: 3050
---
# invoice_account_select

Seleciona conta pagadora.

`act:invoice_account_select`

## Vai para
- (navega) [[screen_invoice_preview-ded64|invoice_preview]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (chama) [[fn_ux.invoice_preview-ea551|invoice_preview]] 
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[fn_ux.invoice_prompt-6a4d0|invoice_prompt]] <conta>
