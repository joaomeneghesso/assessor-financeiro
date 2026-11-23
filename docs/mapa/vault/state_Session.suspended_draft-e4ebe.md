---
tipo: state
arquivo: telegram_experiencia.py
linha: 377
---
# Session.suspended_draft

Rascunho pausado (+suspended_stage/view) por _suspend_flow; retomado por resume_suspended.

`state:Session.suspended_draft`

## Vem de
- (grava_estado) [[act_discard_suspended-3db5a|discard_suspended]] 
- (grava_estado) [[act_discard_and_start-8d1d6|discard_and_start]] 
- (grava_estado) [[act_discard_and_register-b6760|discard_and_register]] 
- (grava_estado) [[fn_ux._suspend_flow-76c4a|_suspend_flow]] 
- (le_estado) [[fn_ux._resume_suspended-db049|_resume_suspended]] 
- (le_estado) [[act_view-1d8b8|view]] 
- (le_estado) [[act_start-ebd45|start]] 
