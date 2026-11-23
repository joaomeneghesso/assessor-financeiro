---
tipo: handler
arquivo: telegram_experiencia.py
linha: 1992
---
# begin

Inicia registro (despesa/receita/simulate/parcelada): cria draft e stage.

`fn:ux.begin`

## Vai para
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (navega) [[fn_ux.prompt-41177|prompt]] 

## Vem de
- (chama) [[act_start-ebd45|start]] 
- (chama) [[act_discard_and_start-8d1d6|discard_and_start]] 
