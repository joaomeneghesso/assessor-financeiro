---
tipo: handler
arquivo: telegram_experiencia.py
linha: 520
---
# _suspend_flow

Pausa draft+stage em suspended_*.

`fn:ux._suspend_flow`

## Vai para
- (grava_estado) [[state_Session.suspended_draft-e4ebe|Session.suspended_draft]] 
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] zera

## Vem de
- (chama) [[fn_ux._ai_query_result-20fe1|_ai_query_result]] 
- (chama) [[act_view-1d8b8|view]] se há stage+draft
- (chama) [[act_topic-518da|topic]] 
- (chama) [[fn_ux.pause_for_guidance-482b6|pause_for_guidance]] 
- (chama) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] 
- (chama) [[text_pagamento_fatura_pausa-fdd8c|pagamento_fatura_pausa]] 
