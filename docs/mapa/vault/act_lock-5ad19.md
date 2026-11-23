---
tipo: action
arquivo: telegram_experiencia.py
linha: 4340
---
# lock

dispatch_callback: invalida sessão e bloqueia assessor.

`act:lock`

## Vai para
- (grava_estado) [[state_Experience.sessions-934fe|Experience.sessions]] invalidate

## Vem de
- (chama) [[fn_ux.dispatch_callback-a9f29|ux.dispatch_callback]] 
- (navega) [[screen_resources-d1f70|resources]] 🔒 Bloquear
- (navega) [[screen_data_tools-d1767|data_tools]] 🔒 Bloquear
