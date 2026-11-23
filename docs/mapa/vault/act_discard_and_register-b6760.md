---
tipo: action
arquivo: telegram_experiencia.py
linha: 2950
---
# discard_and_register

Descarta pausado e abre Registrar.

`act:discard_and_register`

## Vai para
- (grava_estado) [[state_Session.suspended_draft-e4ebe|Session.suspended_draft]] 
- (navega) [[screen_register-1389d|register]] 
- (grava_estado) [[state_Session.suspended_stage-bae0e|Session.suspended_stage]] 
- (grava_estado) [[state_Session.suspended_view-3a7f1|Session.suspended_view]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[act_view-1d8b8|view]] botão da resposta
