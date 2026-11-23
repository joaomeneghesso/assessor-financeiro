---
tipo: action
arquivo: telegram_experiencia.py
linha: 2928
---
# flow_resume

Retoma registro após ajuda.

`act:flow_resume`

## Vai para
- (chama) [[fn_ux.preview-35809|preview]] 
- (chama) [[fn_ux.prompt-41177|prompt]] 
- (le_estado) [[state_Session.draft-81d88|Session.draft]] 
- (le_estado) [[state_Session.stage-ad71b|Session.stage]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[fn_ux._flow_help_screen-a5285|_flow_help_screen]] ↩ Retomar registro
