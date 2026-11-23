---
tipo: handler
arquivo: telegram_alertas.py
linha: 55
---
# telegram_alertas.callback

telegram_alertas: callbacks af:

`fn:telegram_alertas.callback`

## Vai para
- (navega) [[cb_af-51179|af:]] 
- (le_estado) [[state_ALERT_ACTIONS-d9136|ALERT_ACTIONS]] 
- (chama) [[fn_telegram_alertas.adiar-a92a0|telegram_alertas.adiar]] 
- (chama) [[fn_telegram_experiencia.act-0d59a|telegram_experiencia.act]] run_experience('act'|'render')

## Vem de
- (chama) [[cb_af-51179|af:]] 
- (chama) [[mod_telegram_alertas.py-deb44|telegram_alertas.py]] 
- (chama) [[mod_app.py-57fef|app.py]] app.py:4806 callback_submenu -> telegram_alertas.callback
