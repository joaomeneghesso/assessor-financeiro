---
tipo: handler
arquivo: telegram_experiencia.py
linha: 2488
---
# installment_schedule

Cronograma paginado de parcelas.

`fn:ux.installment_schedule`

## Vai para
- (chama) [[fn_telegram_registros.validar_transacao-8ba78|telegram_registros.validar_transacao]] 
- (chama) [[fn_ux.preview-35809|preview]] 
- (chama) [[fn_ux.payload-2099f|ux.payload]] 
- (le_estado) [[state_Session.draft-81d88|Session.draft]] 
- (chama) [[act_installment_schedule-2acd8|installment_schedule]] 
- (chama) [[act_preview-5365c|preview]] 
- (chama) [[act_cancel-c6497|cancel]] 
- (chama) [[act_view-1d8b8|view]] 

## Vem de
- (chama) [[act_installment_schedule-2acd8|installment_schedule]] 
