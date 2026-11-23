---
tipo: action
arquivo: telegram_experiencia.py
linha: 3082
---
# repeat

Repetir lançamento como novo registro.

`act:repeat`

## Vai para
- (chama) [[fn_db.buscar_transacao_por_id-d0e04|buscar_transacao_por_id]] 
- (navega) [[fn_ux.preview-35809|preview]] 
- (chama) [[fn_ux._paused_draft_guard-95346|ux._paused_draft_guard]] 
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_transaction-cd364|transaction]] Repetir como novo registro
- (navega) [[act_commit-ada76|commit]] botão da resposta
