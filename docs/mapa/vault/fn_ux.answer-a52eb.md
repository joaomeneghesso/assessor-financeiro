---
tipo: handler
arquivo: telegram_experiencia.py
linha: 2265
---
# answer

Resposta de texto a etapas (cash_setup, saldo inicial, alert_hours, budget, search, registro, fatura).

`fn:ux.answer`

## Vai para
- (le_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (grava_estado) [[state_Session.search-c5f30|Session.search]] stage=search
- (grava_estado) [[state_Session.pay_account_filter-280ee|Session.pay_account_filter]] stage=account_search
- (grava_estado) [[state_Session.history_account_filter-0cdca|Session.history_account_filter]] stage=account_search
- (chama) [[fn_saldos_edicao.capturar-a2e33|capturar]] 
- (navega) [[fn_ux.prompt-41177|prompt]] 
- (navega) [[fn_ux.preview-35809|preview]] 
- (navega) [[fn_ux.invoice_prompt-6a4d0|invoice_prompt]] 

## Vem de
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] stage ativo
- (chama) [[act_answer-596e5|answer]] 
