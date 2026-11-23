---
tipo: action
arquivo: telegram_experiencia.py
linha: 3401
---
# commit

GRAVA registro (confirmar_registro); grava Session.month = mês da data.

`act:commit`

## Vai para
- (chama) [[fn_telegram_registros.confirmar_registro-9a9b2|telegram_registros.confirmar_registro]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.2882 s.month=mês da data do registro
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] zera
- (grava_estado) [[state_Session.last_event-a12b9|Session.last_event]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (chama) [[fn_ux._aviso_limite-3eb5c|ux._aviso_limite]] 
- (chama) [[fn_ux._apply_privacy-1d25f|ux._apply_privacy]] 
- (chama) [[fn_ux._registration_stage-7351f|ux._registration_stage]] 
- (chama) [[fn_ux._advance_registration-9403a|ux._advance_registration]] 
- (chama) [[fn_ux.payload-2099f|ux.payload]] 
- (navega) [[act_undo_preview-52def|undo_preview]] botão da resposta
- (navega) [[act_cat_menu-e3fc1|cat_menu]] botão da resposta
- (navega) [[act_repeat-a98e8|repeat]] botão da resposta
- (navega) [[act_view-1d8b8|view]] botão da resposta
- (navega) [[act_pay_account_detail-6c538|pay_account_detail]] botão da resposta

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[fn_ux.preview-35809|preview]] ✅ Salvar despesa/entrada
