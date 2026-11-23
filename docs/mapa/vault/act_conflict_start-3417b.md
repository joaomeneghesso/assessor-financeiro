---
tipo: action
arquivo: telegram_experiencia.py
linha: 2937
---
# conflict_start

Descarta o registro atual e começa o novo.

`act:conflict_start`

## Vai para
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 
- (grava_estado) [[state_Session.new_fixed-b5c04|Session.new_fixed]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (grava_estado) [[state_Session.media_review-1b659|Session.media_review]] 
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
- (navega) [[act_view-1d8b8|view]] botão da resposta
