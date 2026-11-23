---
tipo: action
arquivo: telegram_experiencia.py
linha: 3038
---
# invoice_pay_total

Pagar saldo total da fatura.

`act:invoice_pay_total`

## Vai para
- (navega) [[fn_ux.invoice_prompt-6a4d0|invoice_prompt]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (grava_estado) [[state_Session.account_choice_page-45779|Session.account_choice_page]] 
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[fn_ux.invoice_prompt-6a4d0|invoice_prompt]] Usar saldo restante
