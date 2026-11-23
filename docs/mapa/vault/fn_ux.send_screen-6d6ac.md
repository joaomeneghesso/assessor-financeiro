---
tipo: handler
arquivo: telegram_experiencia.py
linha: 4793
---
# send_screen

Envia/edita mensagem: tokens_for -> InlineKeyboard (callback_data=ux:...), copy_text, send_rich, foto (screen.image), proteção de conteúdo.

`fn:ux.send_screen`

## Vai para
- (chama) [[fn_ux.tokens_for-f67d6|Experience.tokens_for]] callback_data=ux:<token>
- (grava_estado) [[state_Session.persist-7ac83|Session.persist]] 

## Vem de
- (chama) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] 
- (chama) [[fn_ux.dispatch_callback-a9f29|ux.dispatch_callback]] edit=True
