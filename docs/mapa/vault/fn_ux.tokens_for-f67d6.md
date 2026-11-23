---
tipo: handler
arquivo: telegram_experiencia.py
linha: 559
---
# Experience.tokens_for

Troca cada ação de botão por token ux:<rand>; limpa tokens antigos (s.tokens.clear()).

`fn:ux.tokens_for`

## Vai para
- (grava_estado) [[state_Session.tokens-0998e|Session.tokens]] clear()+novos tokens

## Vem de
- (le_estado) [[act_copy_text-219aa|copy_text]] sem token: botão nativo
- (chama) [[fn_ux.send_screen-6d6ac|send_screen]] callback_data=ux:<token>
