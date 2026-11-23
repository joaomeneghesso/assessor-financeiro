---
tipo: handler
arquivo: telegram_experiencia.py
linha: 3567
---
# _flow_help_screen

Ajuda durante registro: Retomar/Cancelar.

`fn:ux._flow_help_screen`

## Vai para
- (navega) [[act_flow_resume-b920b|flow_resume]] ↩ Retomar registro
- (navega) [[act_cancel-c6497|cancel]] Cancelar registro
- (le_estado) [[state_Session.stage-ad71b|Session.stage]] 

## Vem de
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
