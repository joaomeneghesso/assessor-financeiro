---
tipo: action
arquivo: telegram_experiencia.py
linha: 3057
---
# invoice_edit_account

Trocar conta pagadora.

`act:invoice_edit_account`

## Vai para
- (navega) [[fn_ux.invoice_prompt-6a4d0|invoice_prompt]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (grava_estado) [[state_Session.account_choice_page-45779|Session.account_choice_page]] 
- (le_estado) [[state_Session.draft-81d88|Session.draft]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_invoice_preview-ded64|invoice_preview]] Trocar conta pagadora
- (chama) [[fn_ux.invoice_preview-ea551|invoice_preview]] 
