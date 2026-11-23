---
tipo: action
arquivo: telegram_experiencia.py
linha: 3364
---
# search

Buscar texto no Histórico (stage=search).

`act:search`

## Vai para
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] search
- (chama) [[fn_ux.prompt-41177|prompt]] 
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_history_tools-cc0f8|history_tools]] 🔎 Buscar texto
- (chama) [[fn_ux._history_tools_screen-c950e|_history_tools_screen]] 
