---
tipo: action
arquivo: telegram_experiencia.py
linha: 2947
---
# discard_and_start

Descarta pausado e inicia novo registro.

`act:discard_and_start`

## Vai para
- (grava_estado) [[state_Session.suspended_draft-e4ebe|Session.suspended_draft]] 
- (chama) [[fn_ux.begin-7f489|begin]] 
- (grava_estado) [[state_Session.suspended_stage-bae0e|Session.suspended_stage]] 
- (grava_estado) [[state_Session.suspended_view-3a7f1|Session.suspended_view]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[act_start-ebd45|start]] botão da resposta
