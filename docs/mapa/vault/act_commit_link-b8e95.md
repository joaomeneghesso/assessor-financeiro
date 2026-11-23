---
tipo: action
arquivo: telegram_experiencia.py
linha: 3319
---
# commit_link

GRAVA vínculo (conc.vincular_existente).

`act:commit_link`

## Vai para
- (chama) [[fn_conciliacao.vincular_existente-f072e|vincular_existente]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 
- (navega) [[act_view-1d8b8|view]] botão da resposta

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[fn_ux.preview-35809|preview]] Confirmar vínculo
